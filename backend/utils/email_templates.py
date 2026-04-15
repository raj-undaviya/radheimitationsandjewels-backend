def settings_email():
    from django.conf import settings
    return settings.EMAIL_HOST_USER

def base_template(content: str, title: str) -> str:
    return f"""
    <!DOCTYPE html>
    <html>
    <head>
      <meta charset="UTF-8">
      <meta name="viewport" content="width=device-width, initial-scale=1.0">
      <title>{title}</title>
    </head>
    <body style="margin:0;padding:0;background:#f5f5f0;font-family:'Georgia',serif;">
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#f5f5f0;padding:40px 20px;">
        <tr><td align="center">
          <table width="580" cellpadding="0" cellspacing="0" style="max-width:580px;width:100%;">

            <!-- Header -->
            <tr>
              <td style="background:#1a1a1a;padding:28px 36px;border-radius:12px 12px 0 0;text-align:center;">
                <p style="margin:0;font-size:11px;letter-spacing:0.15em;color:#c8a97e;text-transform:uppercase;font-family:Arial,sans-serif;">Radhe Imitations & Jewels</p>
                <h1 style="margin:6px 0 0;font-size:22px;color:#ffffff;font-weight:400;letter-spacing:0.05em;">{title}</h1>
              </td>
            </tr>

            <!-- Gold divider -->
            <tr>
              <td style="background:#c8a97e;height:3px;"></td>
            </tr>

            <!-- Body -->
            <tr>
              <td style="background:#ffffff;padding:36px;border-radius:0 0 12px 12px;">
                {content}

                <!-- Footer -->
                <table width="100%" cellpadding="0" cellspacing="0" style="margin-top:36px;padding-top:24px;border-top:1px solid #f0ede8;">
                  <tr>
                    <td align="center">
                      <p style="margin:0;font-size:12px;color:#999;font-family:Arial,sans-serif;">Questions? Reply to this email or contact us at</p>
                      <p style="margin:4px 0 0;font-size:12px;color:#c8a97e;font-family:Arial,sans-serif;">{settings_email()}</p>
                      <p style="margin:16px 0 0;font-size:11px;color:#bbb;font-family:Arial,sans-serif;">© 2026 Radhe Imitations & Jewels. All rights reserved.</p>
                    </td>
                  </tr>
                </table>
              </td>
            </tr>

          </table>
        </td></tr>
      </table>
    </body>
    </html>
    """



def appointment_booked_template(name, date, time_slot, appointment_type):
    type_label = "Virtual Call" if appointment_type == "virtual" else "In-Store Visit"
    content = f"""
      <p style="margin:0 0 20px;font-size:16px;color:#333;font-family:Arial,sans-serif;">Dear <strong>{name}</strong>,</p>
      <p style="margin:0 0 24px;font-size:15px;color:#555;font-family:Arial,sans-serif;line-height:1.7;">
        Thank you for choosing Radhe Imitations & Jewels. Your appointment has been successfully booked. We look forward to assisting you.
      </p>

      <!-- Appointment details box -->
      <table width="100%" cellpadding="0" cellspacing="0" style="background:#faf8f5;border:1px solid #ede8e0;border-radius:8px;margin-bottom:24px;">
        <tr><td style="padding:24px;">
          <p style="margin:0 0 16px;font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#c8a97e;font-family:Arial,sans-serif;">Appointment Details</p>
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td style="padding:8px 0;border-bottom:1px solid #ede8e0;font-size:13px;color:#888;font-family:Arial,sans-serif;width:40%;">Date</td>
              <td style="padding:8px 0;border-bottom:1px solid #ede8e0;font-size:14px;color:#1a1a1a;font-family:Arial,sans-serif;font-weight:bold;">{date}</td>
            </tr>
            <tr>
              <td style="padding:8px 0;border-bottom:1px solid #ede8e0;font-size:13px;color:#888;font-family:Arial,sans-serif;">Time</td>
              <td style="padding:8px 0;border-bottom:1px solid #ede8e0;font-size:14px;color:#1a1a1a;font-family:Arial,sans-serif;font-weight:bold;">{time_slot}</td>
            </tr>
            <tr>
              <td style="padding:8px 0;font-size:13px;color:#888;font-family:Arial,sans-serif;">Type</td>
              <td style="padding:8px 0;font-size:14px;color:#1a1a1a;font-family:Arial,sans-serif;font-weight:bold;">{type_label}</td>
            </tr>
          </table>
        </td></tr>
      </table>

      <p style="margin:0 0 8px;font-size:14px;color:#555;font-family:Arial,sans-serif;line-height:1.7;">
        Our team will confirm your appointment shortly. If you have any questions, feel free to reach out.
      </p>
    """
    return base_template(content, "Appointment Confirmed")


def appointment_confirmed_template(name, date, time_slot, appointment_type):
    type_label = "Virtual Call" if appointment_type == "virtual" else "In-Store Visit"
    content = f"""
      <p style="margin:0 0 20px;font-size:16px;color:#333;font-family:Arial,sans-serif;">Dear <strong>{name}</strong>,</p>
      <p style="margin:0 0 24px;font-size:15px;color:#555;font-family:Arial,sans-serif;line-height:1.7;">
        Great news! Your appointment has been <strong style="color:#2d7a4f;">confirmed</strong> by our team. We are excited to meet you.
      </p>

      <table width="100%" cellpadding="0" cellspacing="0" style="background:#faf8f5;border:1px solid #ede8e0;border-radius:8px;margin-bottom:24px;">
        <tr><td style="padding:24px;">
          <p style="margin:0 0 16px;font-size:11px;letter-spacing:0.12em;text-transform:uppercase;color:#c8a97e;font-family:Arial,sans-serif;">Your Confirmed Appointment</p>
          <table width="100%" cellpadding="0" cellspacing="0">
            <tr>
              <td style="padding:8px 0;border-bottom:1px solid #ede8e0;font-size:13px;color:#888;font-family:Arial,sans-serif;width:40%;">Date</td>
              <td style="padding:8px 0;border-bottom:1px solid #ede8e0;font-size:14px;color:#1a1a1a;font-family:Arial,sans-serif;font-weight:bold;">{date}</td>
            </tr>
            <tr>
              <td style="padding:8px 0;border-bottom:1px solid #ede8e0;font-size:13px;color:#888;font-family:Arial,sans-serif;">Time</td>
              <td style="padding:8px 0;border-bottom:1px solid #ede8e0;font-size:14px;color:#1a1a1a;font-family:Arial,sans-serif;font-weight:bold;">{time_slot}</td>
            </tr>
            <tr>
              <td style="padding:8px 0;font-size:13px;color:#888;font-family:Arial,sans-serif;">Type</td>
              <td style="padding:8px 0;font-size:14px;color:#1a1a1a;font-family:Arial,sans-serif;font-weight:bold;">{type_label}</td>
            </tr>
          </table>
        </td></tr>
      </table>

      <!-- CTA for virtual -->
      {"<p style='margin:0;padding:16px;background:#1a1a1a;border-radius:8px;font-size:13px;color:#c8a97e;font-family:Arial,sans-serif;text-align:center;'>We will send you the virtual call link 30 minutes before your appointment.</p>" if appointment_type == 'virtual' else "<p style='margin:0;padding:16px;background:#faf8f5;border-radius:8px;font-size:13px;color:#555;font-family:Arial,sans-serif;text-align:center;'>Please arrive 5 minutes early at our store. We look forward to seeing you!</p>"}
    """
    return base_template(content, "Appointment Confirmed")


def appointment_cancelled_template(name, date, time_slot):
    content = f"""
      <p style="margin:0 0 20px;font-size:16px;color:#333;font-family:Arial,sans-serif;">Dear <strong>{name}</strong>,</p>
      <p style="margin:0 0 24px;font-size:15px;color:#555;font-family:Arial,sans-serif;line-height:1.7;">
        We regret to inform you that your appointment scheduled for <strong>{date}</strong> at <strong>{time_slot}</strong> has been <strong style="color:#a32d2d;">cancelled</strong>.
      </p>
      <p style="margin:0 0 24px;font-size:14px;color:#555;font-family:Arial,sans-serif;line-height:1.7;">
        We apologize for any inconvenience. Please feel free to book a new appointment at your convenience.
      </p>
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr><td align="center" style="padding:8px 0;">
          <a href="https://radheimitationsandjewels.com/appointments" style="display:inline-block;padding:12px 32px;background:#c8a97e;color:#1a1a1a;text-decoration:none;border-radius:6px;font-size:14px;font-family:Arial,sans-serif;font-weight:bold;letter-spacing:0.05em;">Book New Appointment</a>
        </td></tr>
      </table>
    """
    return base_template(content, "Appointment Cancelled")


def appointment_completed_template(name, date):
    content = f"""
      <p style="margin:0 0 20px;font-size:16px;color:#333;font-family:Arial,sans-serif;">Dear <strong>{name}</strong>,</p>
      <p style="margin:0 0 24px;font-size:15px;color:#555;font-family:Arial,sans-serif;line-height:1.7;">
        Thank you for visiting us on <strong>{date}</strong>. It was a pleasure serving you. We hope you loved your experience with Radhe Imitations & Jewels.
      </p>
      <p style="margin:0 0 24px;font-size:14px;color:#555;font-family:Arial,sans-serif;line-height:1.7;">
        We would love to see you again. Browse our latest collection or book another appointment anytime.
      </p>
      <table width="100%" cellpadding="0" cellspacing="0">
        <tr><td align="center" style="padding:8px 0;">
          <a href="https://radheimitationsandjewels.com" style="display:inline-block;padding:12px 32px;background:#1a1a1a;color:#c8a97e;text-decoration:none;border-radius:6px;font-size:14px;font-family:Arial,sans-serif;font-weight:bold;letter-spacing:0.05em;">Explore Collection</a>
        </td></tr>
      </table>
    """
    return base_template(content, "Thank You for Visiting Us")