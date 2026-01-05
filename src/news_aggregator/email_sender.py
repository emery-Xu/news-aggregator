"""Email sending component using SMTP."""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from datetime import datetime

from .config import SMTPConfig
from .models import EmailContent
from .logger import get_logger


class EmailSender:
    """Sends emails via SMTP."""

    def __init__(self, smtp_config: SMTPConfig):
        """
        Initialize email sender.

        Args:
            smtp_config: SMTP server configuration
        """
        self.config = smtp_config
        self.logger = get_logger()

    def send(self, to: str, content: EmailContent, max_retries: int = 2) -> bool:
        """
        Send email via SMTP with retry logic.

        Args:
            to: Recipient email address
            content: Email content (subject and body)
            max_retries: Maximum number of retry attempts

        Returns:
            True if email was sent successfully, False otherwise
        """
        for attempt in range(max_retries):
            try:
                # Create message
                msg = self._create_message(to, content)

                # Connect and send
                server = None
                try:
                    if self.config.use_tls:
                        # STARTTLS on port 587
                        server = smtplib.SMTP(self.config.host, self.config.port, timeout=30)
                        server.starttls()
                    else:
                        # SSL on port 465
                        server = smtplib.SMTP_SSL(self.config.host, self.config.port, timeout=30)
                    
                    server.login(self.config.username, self.config.password)
                    server.send_message(msg)
                    
                    self.logger.info(f"Email sent successfully to {to}")
                    
                    # Try to quit gracefully, but don't fail if the server already closed the connection
                    try:
                        server.quit()
                    except:
                        pass
                        
                    return True

                except (smtplib.SMTPAuthenticationError) as e:
                    self.logger.error(f"SMTP authentication failed: {e}")
                    return False

                except (smtplib.SMTPException, ConnectionError, OSError) as e:
                    self.logger.warning(
                        f"SMTP connection issue on attempt {attempt + 1}/{max_retries}: {e}"
                    )
                self.logger.warning(
                    f"SMTP error on attempt {attempt + 1}/{max_retries}: {e}"
                )
                if attempt < max_retries - 1:
                    # Wait before retry
                    import time
                    time.sleep(30)
                else:
                    self.logger.error(f"Failed to send email after {max_retries} attempts")
                    return False

            except Exception as e:
                self.logger.error(f"Unexpected error sending email: {e}")
                return False

        return False

    def _create_message(self, to: str, content: EmailContent) -> MIMEMultipart:
        """
        Create email message.

        Args:
            to: Recipient email address
            content: Email content

        Returns:
            MIME message ready to send
        """
        msg = MIMEMultipart('alternative')
        msg['Subject'] = content.subject
        msg['From'] = self.config.from_email
        msg['To'] = to

        # Add plain text part
        part1 = MIMEText(content.plain_text_body, 'plain', 'utf-8')
        msg.attach(part1)

        # Add HTML part (should be last for email clients to prefer it)
        part2 = MIMEText(content.html_body, 'html', 'utf-8')
        msg.attach(part2)

        return msg

    def save_to_file(self, content: EmailContent, output_dir: Path = Path("data/failed_emails")) -> Path:
        """
        Save email to file when sending fails.

        Args:
            content: Email content to save
            output_dir: Directory to save failed emails

        Returns:
            Path to saved email file
        """
        try:
            # Create output directory
            output_dir.mkdir(parents=True, exist_ok=True)

            # Generate filename with timestamp
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"email_{timestamp}.html"
            filepath = output_dir / filename

            # Save HTML content
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"<!-- Subject: {content.subject} -->\n")
                f.write(content.html_body)

            self.logger.info(f"Saved failed email to {filepath}")
            return filepath

        except Exception as e:
            self.logger.error(f"Failed to save email to file: {e}")
            raise
