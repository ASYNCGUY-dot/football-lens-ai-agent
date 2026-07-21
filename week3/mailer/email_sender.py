# -*- coding: utf-8 -*-
"""
email_sender.py
===============
smtplib 기반 축구 뉴스 보고서 이메일 자동 발송 모듈

지원 SMTP:
    - Gmail    : smtp.gmail.com:587 (TLS)
    - 네이버 메일: smtp.naver.com:465 (SSL)
    - 기타     : .env에서 SMTP_HOST/PORT 자유 설정

Gmail 앱 비밀번호 발급:
    1. Google 계정 → 보안 → 2단계 인증 활성화
    2. 보안 → 앱 비밀번호 → 새 앱 비밀번호 생성
    3. .env의 SMTP_PASSWORD에 16자리 앱 비밀번호 입력

사용법:
    from week3.email.email_sender import EmailSender

    sender = EmailSender()
    sender.send_report(
        report_markdown="# ⚽ 보고서...",
        recipients=["me@gmail.com"],
        subject="Football Lens 일간 보고서",
    )
"""

import os
import logging
import smtplib
import ssl
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
from typing import Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


# =============================================
# HTML 이메일 템플릿
# =============================================

def _markdown_to_html_body(markdown_text: str) -> str:
    """
    마크다운 텍스트를 Clean & Sporty 스타일 HTML 이메일로 변환합니다.

    디자인 시스템:
        헤더   : 다크 네이비 배너 + 네온 그린 강조선
        섹션   : 흰색 카드, 왼쪽 초록 테두리
        폰트   : Apple SD Gothic Neo / Malgun Gothic
        강조   : #00C853 (초록)

    변환 규칙:
        #    → 섹션 제목 (대형)
        ##   → 카드 헤더 (중형, 초록 밑줄)
        ###  → 소제목
        **   → <strong>
        *    → <em>
        `    → <code>
        -    → 리스트 항목
        ---  → 구분선

    Parameters
    ----------
    markdown_text : str
        변환할 마크다운 텍스트

    Returns
    -------
    str
        완성된 HTML 이메일 문서 (<html>...</html>)
    """
    import re

    lines = markdown_text.split("\n")
    html_lines = []
    in_list = False

    for line in lines:
        is_list_item = line.lstrip().startswith("- ") or re.match(r'^\d+\.', line.lstrip())

        # 리스트 닫기
        if in_list and not is_list_item:
            html_lines.append(
                '</ul></div>'
            )
            in_list = False

        if line.startswith("### "):
            text = line[4:]
            html_lines.append(
                f'<h3 style="font-size:14px;font-weight:700;color:#1A2744;margin:16px 0 6px;">{text}</h3>'
            )
        elif line.startswith("## "):
            text = line[3:]
            html_lines.append(
                f'<div style="font-size:15px;font-weight:800;color:#0D1117;'
                f'border-left:3px solid #00C853;padding:6px 0 6px 12px;'
                f'margin:20px 0 10px;letter-spacing:-0.3px;">{text}</div>'
            )
        elif line.startswith("# "):
            text = line[2:]
            html_lines.append(
                f'<div style="font-size:18px;font-weight:900;color:#0D1117;'
                f'margin:8px 0 16px;letter-spacing:-0.5px;line-height:1.3;">{text}</div>'
            )
        elif line.strip() == "---":
            html_lines.append(
                '<div style="height:1px;background:linear-gradient(90deg,#00C853,#E8F5E9,transparent);'
                'margin:20px 0;"></div>'
            )
        elif line.strip() == "":
            if not in_list:
                html_lines.append('<div style="height:8px;"></div>')
        elif is_list_item:
            # 리스트 열기
            if not in_list:
                html_lines.append(
                    '<div style="background:#F8FFF9;border-radius:8px;padding:10px 14px;margin:8px 0;">'
                    '<ul style="margin:0;padding-left:18px;list-style:none;">'
                )
                in_list = True
            # 항목 텍스트 추출
            if line.lstrip().startswith("- "):
                item_text = line.lstrip()[2:]
            else:
                item_text = re.sub(r'^\d+\.\s*', '', line.lstrip())
            # 인라인 변환
            item_text = re.sub(r'\*\*(.+?)\*\*', r'<strong style="color:#0D4A2B;">\1</strong>', item_text)
            item_text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', item_text)
            item_text = re.sub(
                r'`(.+?)`',
                r'<code style="background:#E8F5E9;color:#1B5E20;padding:1px 5px;border-radius:4px;font-size:11px;">\1</code>',
                item_text,
            )
            html_lines.append(
                f'<li style="font-size:13px;color:#374151;padding:3px 0;line-height:1.6;">'
                f'<span style="color:#00C853;margin-right:6px;font-size:10px;">▶</span>{item_text}</li>'
            )
        else:
            converted = line
            converted = re.sub(r'\*\*(.+?)\*\*', r'<strong style="color:#0D1117;">\1</strong>', converted)
            converted = re.sub(r'\*(.+?)\*', r'<em style="color:#374151;">\1</em>', converted)
            converted = re.sub(
                r'`(.+?)`',
                r'<code style="background:#F0FFF4;color:#1B5E20;padding:1px 5px;border-radius:4px;font-size:11px;">\1</code>',
                converted,
            )
            html_lines.append(
                f'<p style="font-size:13px;color:#4B5563;line-height:1.75;margin:4px 0;">{converted}</p>'
            )

    # 마지막 리스트 닫기
    if in_list:
        html_lines.append('</ul></div>')

    body_content = "\n".join(html_lines)
    now_str = datetime.now().strftime("%Y년 %m월 %d일")

    return f"""<!DOCTYPE html>
<html lang="ko">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Football Lens 보고서</title>
</head>
<body style="margin:0;padding:0;background-color:#F0F4F8;
             font-family:'Apple SD Gothic Neo','Malgun Gothic','Noto Sans KR',sans-serif;">

  <table width="100%" cellpadding="0" cellspacing="0" style="padding:32px 16px;">
    <tr>
      <td align="center">
        <table width="620" cellpadding="0" cellspacing="0"
               style="max-width:620px;width:100%;border-radius:16px;
                      overflow:hidden;box-shadow:0 4px 24px rgba(0,0,0,0.12);">

          <!-- ① 헤더 배너 -->
          <tr>
            <td style="background:linear-gradient(135deg,#0D1117 0%,#1A2744 55%,#0B2818 100%);
                       padding:28px 32px;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td style="vertical-align:middle;">
                    <div style="font-size:30px;margin-bottom:4px;">⚽</div>
                    <div style="font-size:20px;font-weight:900;color:#F8FAFC;
                                letter-spacing:-0.5px;line-height:1.2;">Football Lens</div>
                    <div style="font-size:10px;color:#00FF87;font-weight:700;
                                letter-spacing:2px;text-transform:uppercase;margin-top:4px;">
                      AI FOOTBALL NEWS REPORT
                    </div>
                  </td>
                  <td align="right" style="vertical-align:top;">
                    <div style="background:rgba(0,255,135,0.12);
                                border:1px solid rgba(0,255,135,0.25);
                                border-radius:10px;padding:8px 14px;display:inline-block;">
                      <div style="font-size:10px;color:#00FF87;font-weight:700;
                                  text-transform:uppercase;letter-spacing:0.5px;">
                        Daily Report
                      </div>
                      <div style="font-size:12px;color:#94A3B8;margin-top:3px;font-weight:500;">
                        {now_str}
                      </div>
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ② 강조선 -->
          <tr>
            <td style="height:3px;
                       background:linear-gradient(90deg,#00C853,#00FF87,#69FFBC);"></td>
          </tr>

          <!-- ③ 뱃지 바 -->
          <tr>
            <td style="background:#111827;padding:10px 32px;">
              <table cellpadding="0" cellspacing="0">
                <tr>
                  <td style="padding-right:8px;">
                    <span style="background:rgba(0,255,135,0.1);border:1px solid rgba(0,255,135,0.25);
                                 border-radius:6px;padding:3px 10px;font-size:10px;color:#00FF87;
                                 font-weight:600;letter-spacing:0.3px;">⚡ LangGraph</span>
                  </td>
                  <td style="padding-right:8px;">
                    <span style="background:rgba(96,165,250,0.1);border:1px solid rgba(96,165,250,0.25);
                                 border-radius:6px;padding:3px 10px;font-size:10px;color:#60A5FA;
                                 font-weight:600;">🤖 Claude + GPT-4o</span>
                  </td>
                  <td>
                    <span style="background:rgba(167,139,250,0.1);border:1px solid rgba(167,139,250,0.25);
                                 border-radius:6px;padding:3px 10px;font-size:10px;color:#A78BFA;
                                 font-weight:600;">🔍 RAG</span>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

          <!-- ④ 본문 -->
          <tr>
            <td style="background:#ffffff;padding:28px 32px 32px;">
              {body_content}
            </td>
          </tr>

          <!-- ⑤ 푸터 -->
          <tr>
            <td style="background:#F8FAFC;padding:20px 32px;border-top:1px solid #E2E8F0;">
              <table width="100%" cellpadding="0" cellspacing="0">
                <tr>
                  <td>
                    <div style="font-size:11px;color:#94A3B8;line-height:1.9;">
                      <div style="font-weight:600;color:#64748B;margin-bottom:2px;">
                        ⚽ Football Lens
                      </div>
                      <div>이 보고서는 AI 에이전트가 자동 생성했습니다.</div>
                      <div style="margin-top:4px;font-size:10px;color:#CBD5E1;">
                        Powered by LangGraph · Claude · GPT-4o-mini · Gemini · ChromaDB
                      </div>
                    </div>
                  </td>
                  <td align="right" style="vertical-align:top;">
                    <div style="width:32px;height:32px;background:linear-gradient(135deg,#00C853,#00FF87);
                                border-radius:50%;text-align:center;line-height:32px;font-size:16px;">
                      ⚽
                    </div>
                  </td>
                </tr>
              </table>
            </td>
          </tr>

        </table>
      </td>
    </tr>
  </table>

</body>
</html>"""


# =============================================
# EmailSender 클래스
# =============================================

class EmailSender:
    """
    smtplib 기반 이메일 발송기

    주요 메서드:
        send_report()   : 보고서 마크다운을 HTML 이메일로 발송
        send_raw()      : 커스텀 제목/본문으로 이메일 발송
        test_connection(): SMTP 연결 테스트

    환경변수:
        SMTP_HOST        : SMTP 서버 주소 (기본: smtp.gmail.com)
        SMTP_PORT        : SMTP 포트 (기본: 587)
        SMTP_USE_SSL     : SSL 사용 여부 (기본: false → TLS)
        SMTP_USER        : 발신자 이메일
        SMTP_PASSWORD    : 앱 비밀번호
        EMAIL_RECIPIENTS : 기본 수신자 (쉼표 구분)
        EMAIL_SENDER_NAME: 발신자 이름 (기본: Football Lens Bot)
    """

    def __init__(
        self,
        host: str = None,
        port: int = None,
        user: str = None,
        password: str = None,
        use_ssl: bool = None,
    ):
        """
        SMTP 설정을 초기화합니다.

        Parameters
        ----------
        host, port, user, password : str/int
            SMTP 연결 정보. 미입력 시 환경변수에서 읽습니다.
        use_ssl : bool
            True=SSL(465포트), False=TLS STARTTLS(587포트)
        """
        self.host = host or os.getenv("SMTP_HOST", "smtp.gmail.com")
        self.port = port or int(os.getenv("SMTP_PORT", "587"))
        self.user = user or os.getenv("SMTP_USER", "")
        self.password = password or os.getenv("SMTP_PASSWORD", "")
        self.sender_name = os.getenv("EMAIL_SENDER_NAME", "Football Lens Bot")

        if use_ssl is None:
            self.use_ssl = os.getenv("SMTP_USE_SSL", "false").lower() == "true"
        else:
            self.use_ssl = use_ssl

        if not self.user or not self.password:
            raise ValueError(
                "SMTP 인증 정보가 없습니다.\n"
                ".env 파일에 SMTP_USER와 SMTP_PASSWORD를 설정하세요.\n"
                "Gmail 앱 비밀번호 발급: "
                "Google 계정 → 보안 → 2단계 인증 → 앱 비밀번호"
            )

    def _create_smtp_connection(self):
        """
        SMTP 연결 객체를 생성하고 로그인합니다.

        Returns
        -------
        smtplib.SMTP or smtplib.SMTP_SSL
            로그인된 SMTP 연결 객체
        """
        if self.use_ssl:
            # SSL 방식 (포트 465, 네이버 등)
            context = ssl.create_default_context()
            smtp = smtplib.SMTP_SSL(self.host, self.port, context=context)
        else:
            # TLS (STARTTLS) 방식 (포트 587, Gmail 등)
            smtp = smtplib.SMTP(self.host, self.port)
            smtp.ehlo()
            smtp.starttls(context=ssl.create_default_context())
            smtp.ehlo()

        smtp.login(self.user, self.password)
        logger.info(f"SMTP 연결 성공: {self.host}:{self.port}")
        return smtp

    def _build_message(
        self,
        recipients: list[str],
        subject: str,
        html_body: str,
        text_body: str = None,
        attachment_path: str = None,
    ) -> MIMEMultipart:
        """
        MIME 이메일 메시지 객체를 구성합니다.

        Parameters
        ----------
        recipients : list[str]
            수신자 목록
        subject : str
            이메일 제목
        html_body : str
            HTML 형식 본문
        text_body : str, optional
            일반 텍스트 본문 (HTML 미지원 클라이언트용)
        attachment_path : str, optional
            첨부 파일 경로

        Returns
        -------
        MIMEMultipart
            완성된 이메일 메시지 객체
        """
        msg = MIMEMultipart("alternative")
        msg["Subject"] = subject
        msg["From"] = f"{self.sender_name} <{self.user}>"
        msg["To"] = ", ".join(recipients)

        # 텍스트 파트 (폴백)
        if text_body:
            msg.attach(MIMEText(text_body, "plain", "utf-8"))

        # HTML 파트
        msg.attach(MIMEText(html_body, "html", "utf-8"))

        # 첨부 파일
        if attachment_path and os.path.exists(attachment_path):
            try:
                with open(attachment_path, "rb") as f:
                    part = MIMEBase("application", "octet-stream")
                    part.set_payload(f.read())
                encoders.encode_base64(part)
                filename = os.path.basename(attachment_path)
                part.add_header(
                    "Content-Disposition",
                    f"attachment; filename={filename}",
                )
                msg.attach(part)
                logger.info(f"첨부 파일 추가: {filename}")
            except Exception as e:
                logger.warning(f"첨부 파일 처리 오류: {e}")

        return msg

    def send_report(
        self,
        report_markdown: str,
        recipients: list[str] = None,
        subject: str = None,
        attachment_path: str = None,
    ) -> bool:
        """
        축구 뉴스 보고서를 HTML 이메일로 발송합니다.

        Parameters
        ----------
        report_markdown : str
            발송할 보고서 마크다운 텍스트
        recipients : list[str], optional
            수신자 목록. 미입력 시 환경변수 EMAIL_RECIPIENTS 사용.
        subject : str, optional
            이메일 제목. 기본값: "⚽ Football Lens 보고서 - 날짜"
        attachment_path : str, optional
            첨부 파일 경로 (예: 보고서 .md 파일)

        Returns
        -------
        bool
            발송 성공 여부
        """
        try:
            # 수신자 결정
            if not recipients:
                default_str = os.getenv("EMAIL_RECIPIENTS", "")
                recipients = [r.strip() for r in default_str.split(",") if r.strip()]
            if not recipients:
                raise ValueError(
                    "수신자 이메일이 없습니다. "
                    "recipients 인자 또는 EMAIL_RECIPIENTS 환경변수를 설정하세요."
                )

            # 제목 기본값
            if not subject:
                subject = f"⚽ Football Lens 보고서 - {datetime.now().strftime('%Y년 %m월 %d일')}"

            # HTML 변환
            html_body = _markdown_to_html_body(report_markdown)

            # 메시지 구성
            msg = self._build_message(
                recipients=recipients,
                subject=subject,
                html_body=html_body,
                text_body=report_markdown,  # 텍스트 폴백
                attachment_path=attachment_path,
            )

            # 발송
            with self._create_smtp_connection() as smtp:
                smtp.sendmail(self.user, recipients, msg.as_string())

            logger.info(f"이메일 발송 완료: {len(recipients)}명 → {recipients}")
            return True

        except ValueError as e:
            logger.error(f"[send_report] 설정 오류: {e}")
            raise
        except smtplib.SMTPAuthenticationError:
            logger.error(
                "[send_report] SMTP 인증 실패. "
                "Gmail 사용 시 앱 비밀번호를 확인하세요."
            )
            raise
        except smtplib.SMTPException as e:
            logger.error(f"[send_report] SMTP 오류: {e}")
            raise
        except Exception as e:
            logger.error(f"[send_report] 이메일 발송 실패: {e}")
            raise

    def send_raw(
        self,
        recipients: list[str],
        subject: str,
        body: str,
        is_html: bool = False,
    ) -> bool:
        """
        커스텀 제목과 본문으로 이메일을 발송합니다.

        Parameters
        ----------
        recipients : list[str]
            수신자 이메일 목록
        subject : str
            이메일 제목
        body : str
            본문 텍스트 (또는 HTML)
        is_html : bool
            True이면 HTML 형식, False이면 일반 텍스트

        Returns
        -------
        bool
            발송 성공 여부
        """
        try:
            msg = MIMEMultipart()
            msg["Subject"] = subject
            msg["From"] = f"{self.sender_name} <{self.user}>"
            msg["To"] = ", ".join(recipients)
            content_type = "html" if is_html else "plain"
            msg.attach(MIMEText(body, content_type, "utf-8"))

            with self._create_smtp_connection() as smtp:
                smtp.sendmail(self.user, recipients, msg.as_string())

            logger.info(f"이메일 발송 완료: {recipients}")
            return True
        except Exception as e:
            logger.error(f"[send_raw] 발송 실패: {e}")
            raise

    def test_connection(self) -> bool:
        """
        SMTP 서버 연결을 테스트합니다.

        Returns
        -------
        bool
            연결 성공 여부
        """
        try:
            with self._create_smtp_connection() as smtp:
                status = smtp.noop()
            logger.info(f"SMTP 연결 테스트 성공: {self.host}:{self.port}")
            return True
        except Exception as e:
            logger.error(f"[test_connection] 연결 실패: {e}")
            return False


# =============================================
# 직접 실행 시 연결 테스트
# =============================================
if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    print("=== EmailSender 테스트 ===\n")
    try:
        sender = EmailSender()
        print(f"SMTP 설정: {sender.host}:{sender.port} (SSL: {sender.use_ssl})")
        print(f"발신자: {sender.user}\n")

        print("연결 테스트 중...")
        if sender.test_connection():
            print("✅ SMTP 연결 성공!\n")

            # 테스트 이메일 발송
            test_report = """# ⚽ Football Lens 테스트 보고서

## 테스트 메시지
이 메일은 EmailSender 모듈 테스트용입니다.

## 주요 내용
- **손흥민**: 챔피언스리그 골 폭발
- **EPL 순위**: 맨시티 1위 유지
- **이강인**: PSG에서 주전 경쟁 중

---
*Football Lens AI 에이전트가 자동 생성한 테스트 메일입니다.*"""

            recipients_str = os.getenv("EMAIL_RECIPIENTS", "")
            if recipients_str:
                recipients = [r.strip() for r in recipients_str.split(",") if r.strip()]
                sender.send_report(
                    report_markdown=test_report,
                    recipients=recipients,
                    subject="⚽ Football Lens 연결 테스트",
                )
                print(f"✅ 테스트 이메일 발송 완료: {recipients}")
            else:
                print("⚠️ EMAIL_RECIPIENTS 환경변수를 설정하면 테스트 이메일을 발송합니다.")
        else:
            print("❌ SMTP 연결 실패")

    except ValueError as e:
        print(f"설정 오류: {e}")
    except Exception as e:
        print(f"오류: {e}")
