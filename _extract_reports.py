# -*- coding: utf-8 -*-
import os
import zipfile
from xml.etree import ElementTree as ET

root = r"C:\Users\16899\Desktop\见习报告1\见习报告"
out_dir = r"C:\Users\16899\Desktop\Personal\_tmp_extract"
os.makedirs(out_dir, exist_ok=True)

W_T = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t"
W_P = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"


def docx_text(path):
    with zipfile.ZipFile(path) as z:
        xml = z.read("word/document.xml")
    root_el = ET.fromstring(xml)
    paras = []
    for p in root_el.iter(W_P):
        texts = [t.text or "" for t in p.iter(W_T)]
        line = "".join(texts).strip()
        if line:
            paras.append(line)
    return "\n".join(paras)


files = [
    "转正申请.txt",
    "2026年2月见习月报-张建领.docx",
    "2026年3月见习月报-张建领.docx",
    "2026年4月见习月报-张建领.docx",
    "2026年5月见习月报-张建领.docx",
    "2026年6月见习月报-张建领.docx",
    "2026年7月见习月报-张建领.docx",
    "2026年1月第一周见习周报-张建领.docx",
    "2026年8月第二十七周见习周报-张建领.docx",
    "2026年8月第二十八周见习周报-张建领.docx",
]

summary_path = os.path.join(out_dir, "_all_summary.txt")
with open(summary_path, "w", encoding="utf-8") as summary:
    for f in files:
        p = os.path.join(root, f)
        summary.write(f"\n======== {f} exists={os.path.exists(p)} ========\n")
        if not os.path.exists(p):
            continue
        if f.endswith(".txt"):
            text = open(p, encoding="utf-8", errors="ignore").read()
        else:
            text = docx_text(p)
        out = os.path.join(out_dir, f.replace(".docx", ".txt").replace(" ", "_"))
        open(out, "w", encoding="utf-8").write(text)
        summary.write(text[:3000])
        summary.write(f"\n...LEN {len(text)}\n")

print("wrote", summary_path)
