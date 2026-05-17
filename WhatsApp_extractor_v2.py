import re
import pdfplumber
import pandas as pd
from datetime import datetime
from collections import defaultdict
from fpdf import FPDF

# -----------------------------
# CONFIG
# -----------------------------
INPUT_PDF = "Gudda_Guddi_WhatsApp_chats.pdf"
OUTPUT_EXCEL = "call_logs_1.xlsx"
OUTPUT_PDF = "call_logs_sorted_1.pdf"

# -----------------------------
# REGEX (handles emojis + (cid:X))
# -----------------------------
pattern = re.compile(r"\[(\d{2}/\d{2}/\d{4}), (\d{2}:\d{2}:\d{2})\]\s(.+?):(?:\(cid:\d+\))?\s*(Voice call|Video call),\s*(.+)",flags=re.UNICODE)

# -----------------------------
# STEP 1: Extract and merge lines
# -----------------------------
merged_lines = []

with pdfplumber.open(INPUT_PDF) as pdf:
    buffer = ""
    for page in pdf.pages:
        text = page.extract_text()
        if not text:
            continue

        for line in text.split("\n"):
            if line.startswith("[") and re.match(r"\[\d{2}/\d{2}/\d{4}, \d{2}:\d{2}:\d{2}\]", line):
                if buffer:
                    merged_lines.append(buffer.strip())
                buffer = line
            else:
                buffer += " " + line.strip()

    if buffer:
        merged_lines.append(buffer.strip())

# -----------------------------
# STEP 2: Match and extract records
# -----------------------------
records = []

for line in merged_lines:
    match = pattern.match(line)
    if match:
        date_str, time_str, name, call_type, duration = match.groups()
        dt = datetime.strptime(f"{date_str} {time_str}", "%d/%m/%Y %H:%M:%S")

        name = name.replace("(cid:4)", "").strip()

        records.append({
            "datetime": dt,
            "date": date_str,
            "time": time_str,
            "name": name,
            "call_type": call_type,
            "duration": duration,
            "raw": line
        })

# -----------------------------
# STEP 3: Sort chronologically
# -----------------------------
records = sorted(records, key=lambda x: x["datetime"])

# -----------------------------
# STEP 4: Save to Excel
# -----------------------------
df = pd.DataFrame(records)
df.to_excel(OUTPUT_EXCEL, index=False)

# -----------------------------
# STEP 5: Group by month
# -----------------------------
grouped = defaultdict(list)
for r in records:
    month_key = r["datetime"].strftime("%Y-%m")
    grouped[month_key].append(r["raw"])

# -----------------------------
# STEP 6: Create Unicode PDF (fpdf2)
# -----------------------------
pdf = FPDF()
pdf.set_auto_page_break(auto=True, margin=15)
pdf.add_page()

pdf.add_font("DejaVu", "", "DejaVuSans.ttf", uni=True)
pdf.set_font("DejaVu", size=12)

for month in sorted(grouped.keys()):
    pdf.set_font("DejaVu", "", 14)
    pdf.cell(0, 10, txt=f"=== {month} ===", ln=True)
    pdf.set_font("DejaVu", "", 12)

    for line in grouped[month]:
        pdf.multi_cell(0, 8, txt=line)

    pdf.ln(5)

pdf.output(OUTPUT_PDF)

print("Extraction complete!")
print(f"Excel saved as: {OUTPUT_EXCEL}")
print(f"PDF saved as: {OUTPUT_PDF}")