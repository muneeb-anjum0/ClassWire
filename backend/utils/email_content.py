"""Shared email content builders for timetable delivery."""

from __future__ import annotations

from typing import Dict, List


def escape_html(value: object) -> str:
    text = "" if value is None else str(value)
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def display_value(value: object, fallback: str = "-") -> str:
    text = str(value or "").strip()
    return text if text else fallback


def build_plain_text(timetable: Dict) -> str:
    items: List[Dict] = timetable.get("items") or []
    lines = [
        f"ClassWire schedule for {timetable.get('for_day', 'today')} ({timetable.get('for_date', '')})",
        "",
    ]

    if not items:
        lines.extend(
            [
                "No Classes Found",
                "",
                "No timetable email matched your configured semesters for this day.",
                "ClassWire will check again at the next scheduled run.",
            ]
        )
        return "\n".join(lines)

    for item in items:
        lines.append(
            f"{display_value(item.get('semester_display') or item.get('semester'))} | "
            f"{display_value(item.get('course_title') or item.get('course'))} | "
            f"{display_value(item.get('faculty'))} | "
            f"{display_value(item.get('room'))} | "
            f"{display_value(item.get('time'))} | "
            f"{display_value(item.get('campus'))}"
        )

    return "\n".join(lines)


def build_subject(timetable: Dict) -> str:
    job_marker = timetable.get("email_job_id")
    suffix = f" [{job_marker[:8]}]" if job_marker else ""
    if not (timetable.get("items") or []):
        return f"ClassWire: No classes found for {timetable.get('for_day', 'today')}{suffix}"
    return f"ClassWire: timetable for {timetable.get('for_day', 'today')}{suffix}"


def _group_items_by_semester(items: List[Dict]) -> Dict[str, List[Dict]]:
    grouped: Dict[str, List[Dict]] = {}
    for item in items:
        semester = display_value(
            item.get("semester_display") or item.get("class_section") or item.get("semester"),
            "Unassigned",
        )
        grouped.setdefault(semester, []).append(item)
    return grouped


def build_timetable_email_html(timetable: Dict, university_email: str) -> str:
    items: List[Dict] = timetable.get("items") or []
    no_classes = len(items) == 0
    summary = timetable.get("summary") or {}
    grouped = _group_items_by_semester(items)
    for semester_items in grouped.values():
        semester_items.sort(key=lambda item: display_value(item.get("time")))

    rows_html = []
    if no_classes:
        rows_html.append(
            """
            <tr>
              <td colspan="5" style="padding:18px;color:#64748b;text-align:center;">
                No classes were found for your configured semesters.
              </td>
            </tr>
            """
        )
    else:
        for semester, semester_items in grouped.items():
            rows_html.append(
                f"""
                <tr>
                  <td colspan="5" style="padding:12px 14px;background:#f8fafc;border-top:1px solid #e2e8f0;border-bottom:1px solid #e2e8f0;color:#0f172a;font-weight:700;">
                    {escape_html(semester)} · {len(semester_items)} class{'es' if len(semester_items) != 1 else ''}
                  </td>
                </tr>
                """
            )
            for item in semester_items:
                course = display_value(item.get("course_title") or item.get("course"))
                course_code = display_value(item.get("course_code") or item.get("course"), "")
                faculty = display_value(item.get("faculty") or item.get("faculty_name"), "TBD")
                room = display_value(item.get("room"), "TBD")
                time = display_value(item.get("time"))
                campus = display_value(item.get("campus"))
                cancelled = "cancelled" in " ".join([course, faculty, room, time, campus]).lower()
                accent = "#dc2626" if cancelled else "#0f172a"

                rows_html.append(
                    f"""
                    <tr>
                      <td style="padding:12px 14px;border-bottom:1px solid #e5e7eb;color:{accent};">
                        <div style="font-weight:700;">{escape_html(course)}</div>
                        <div style="margin-top:3px;color:#64748b;font-size:12px;">{escape_html(course_code)}</div>
                      </td>
                      <td style="padding:12px 14px;border-bottom:1px solid #e5e7eb;color:#334155;">{escape_html(faculty)}</td>
                      <td style="padding:12px 14px;border-bottom:1px solid #e5e7eb;color:#334155;">{escape_html(room)}</td>
                      <td style="padding:12px 14px;border-bottom:1px solid #e5e7eb;color:#334155;white-space:nowrap;">{escape_html(time)}</td>
                      <td style="padding:12px 14px;border-bottom:1px solid #e5e7eb;color:#334155;">{escape_html(campus)}</td>
                    </tr>
                    """
                )

    empty_state_html = ""
    if no_classes:
        empty_state_html = f"""
            <div style="padding:24px 20px;background:#ffffff;">
              <div style="border:1px solid #dbeafe;background:linear-gradient(135deg,#eff6ff 0%,#f8fafc 45%,#ecfdf5 100%);border-radius:18px;padding:24px;text-align:center;">
                <div style="display:inline-block;padding:7px 12px;border-radius:999px;background:#ffffff;border:1px solid #bfdbfe;color:#2563eb;font-size:12px;font-weight:700;letter-spacing:0.08em;text-transform:uppercase;">
                  Clear schedule
                </div>
                <h2 style="margin:14px 0 8px;color:#0f172a;font-size:26px;line-height:1.2;">No Classes Found</h2>
                <p style="max-width:560px;margin:0 auto;color:#475569;font-size:15px;line-height:1.55;">
                  ClassWire checked your Gmail for {escape_html(timetable.get('for_day', 'today'))} and did not find any matching classes for your configured semesters.
                </p>
                <div style="margin-top:18px;display:inline-block;padding:10px 14px;border-radius:12px;background:#ffffff;color:#0f172a;border:1px solid #e2e8f0;font-size:14px;">
                  We will check again automatically at the next daily run.
                </div>
              </div>
            </div>
        """

    return f"""
    <!doctype html>
    <html>
      <body style="margin:0;padding:0;background:#f1f5f9;font-family:Arial,Helvetica,sans-serif;color:#0f172a;">
        <div style="max-width:920px;margin:0 auto;padding:28px 14px;">
          <div style="background:#ffffff;border:1px solid #e2e8f0;border-radius:18px;overflow:hidden;box-shadow:0 18px 42px rgba(15,23,42,0.08);">
            <div style="padding:24px;background:#0f172a;color:#ffffff;">
              <div style="font-size:12px;letter-spacing:0.12em;text-transform:uppercase;color:#cbd5e1;">ClassWire</div>
              <h1 style="margin:8px 0 0;font-size:24px;line-height:1.2;">Your timetable for {escape_html(timetable.get('for_day', 'today'))}</h1>
              <p style="margin:8px 0 0;color:#cbd5e1;font-size:14px;">Generated for {escape_html(university_email)} · {escape_html(timetable.get('for_date', ''))}</p>
            </div>

            {empty_state_html}

            <div style="display:flex;gap:10px;flex-wrap:wrap;padding:16px 20px;background:#f8fafc;border-bottom:1px solid #e2e8f0;">
              <span style="padding:8px 10px;border-radius:999px;background:#ffffff;border:1px solid #e2e8f0;font-size:13px;"><strong>{escape_html(summary.get('total_items', len(items)))}</strong> classes</span>
              <span style="padding:8px 10px;border-radius:999px;background:#ffffff;border:1px solid #e2e8f0;font-size:13px;"><strong>{escape_html(summary.get('unique_courses', 0))}</strong> unique courses</span>
              <span style="padding:8px 10px;border-radius:999px;background:#ffffff;border:1px solid #e2e8f0;font-size:13px;"><strong>{escape_html(summary.get('unique_faculty', 0))}</strong> faculty</span>
            </div>

            <div style="overflow-x:auto;">
              <table role="presentation" cellspacing="0" cellpadding="0" style="width:100%;border-collapse:collapse;font-size:14px;">
                <thead>
                  <tr style="background:#ffffff;">
                    <th align="left" style="padding:13px 14px;border-bottom:1px solid #e2e8f0;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:0.08em;">Course</th>
                    <th align="left" style="padding:13px 14px;border-bottom:1px solid #e2e8f0;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:0.08em;">Faculty</th>
                    <th align="left" style="padding:13px 14px;border-bottom:1px solid #e2e8f0;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:0.08em;">Room</th>
                    <th align="left" style="padding:13px 14px;border-bottom:1px solid #e2e8f0;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:0.08em;">Time</th>
                    <th align="left" style="padding:13px 14px;border-bottom:1px solid #e2e8f0;color:#64748b;font-size:11px;text-transform:uppercase;letter-spacing:0.08em;">Campus</th>
                  </tr>
                </thead>
                <tbody>
                  {''.join(rows_html)}
                </tbody>
              </table>
            </div>

            <div style="padding:16px 20px;color:#64748b;font-size:12px;background:#ffffff;">
              This automated email was sent because daily delivery is enabled in ClassWire.
            </div>
          </div>
        </div>
      </body>
    </html>
    """
