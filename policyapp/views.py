import os
import tempfile
from django.shortcuts import render, redirect, get_object_or_404
from .models import PolicyAnalysis
from PyPDF2 import PdfReader
from pdf2image import convert_from_path
from PIL import Image
import pytesseract
from openai import OpenAI

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key="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"
)


def extract_text_from_pdf(pdf_path):
    try:
        reader = PdfReader(pdf_path)
        text = ""
        for page in reader.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text

        # Fallback to OCR if PyPDF2 failed
        if len(text.strip()) < 100:
            print("Fallback to OCR...")
            images = convert_from_path(pdf_path)
            ocr_text = ""
            for img in images:
                ocr_text += pytesseract.image_to_string(img)
            return ocr_text.strip()[:10000]

        return text.strip()[:10000]
    except Exception as e:
        return f"[Error reading PDF: {e}]"

def extract_policy_info(text):
    prompt = f"""
You are a helpful assistant. Extract the following details from the policy text below:

1. **Date the policy was established**
2. **Title of the policy**
3. **Summary** (at least two paragraphs)
4. **Sectors it impacts** - list one per line with an explanation of how that sector is impacted.
5. **Most impacted sector** with a detailed explanation why.

Respond in this format exactly:
Date Established: ...
Title: ...
Summary:
[paragraphs]
Impacted Sectors:
- 🏥 Healthcare: ...
- 🎓 Education: ...
Most Impacted Sector:
...

Policy Text:
{text}
"""
    response = client.chat.completions.create(
        model="mistralai/mixtral-8x7b-instruct",
        messages=[{"role": "user", "content": prompt}],
        temperature=0.5,
        max_tokens=2000
    )

    content = response.choices[0].message.content

    info = {
        "date_established": "",
        "title": "",
        "summary": "",
        "impacted_sectors": [],
        "most_impacted_sector": ""
    }

    lines = content.splitlines()
    current_section = None
    summary_lines = []

    for line in lines:
        line = line.strip()
        if line.startswith("Date Established:"):
            info["date_established"] = line.replace("Date Established:", "").strip()
        elif line.startswith("Title:"):
            info["title"] = line.replace("Title:", "").strip()
        elif line.startswith("Summary:"):
            current_section = "summary"
        elif line.startswith("Impacted Sectors:"):
            current_section = "impacted_sectors"
        elif line.startswith("Most Impacted Sector:"):
            current_section = "most_impacted_sector"
        else:
            if current_section == "summary":
                summary_lines.append(line)
            elif current_section == "impacted_sectors" and line.startswith("-"):
                info["impacted_sectors"].append(line[1:].strip())
            elif current_section == "most_impacted_sector":
                info["most_impacted_sector"] += line + " "

    info["summary"] = "\n".join(summary_lines).strip()
    info["most_impacted_sector"] = info["most_impacted_sector"].strip()

    return info

def home(request):
    if request.method == "POST" and request.FILES.get("pdf_file"):
        uploaded_pdf = request.FILES["pdf_file"]
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_file:
            for chunk in uploaded_pdf.chunks():
                temp_file.write(chunk)
            temp_path = temp_file.name

        try:
            text = extract_text_from_pdf(temp_path)
            extracted = extract_policy_info(text)

            policy = PolicyAnalysis.objects.create(
                pdf_file=uploaded_pdf,
                date_established=extracted["date_established"],
                title=extracted["title"],
                summary=extracted["summary"],
                impacted_sectors="\n".join(extracted["impacted_sectors"]),
                most_impacted_sector=extracted["most_impacted_sector"]
            )

            return redirect("view_policy", pk=policy.pk)

        except Exception as e:
            return render(request, "policyapp/result.html", {"error": str(e)})

    return render(request, "policyapp/result.html")

def delete_policy(request, pk):
    policy = get_object_or_404(PolicyAnalysis, pk=pk)
    if policy.pdf_file and os.path.exists(policy.pdf_file.path):
        os.remove(policy.pdf_file.path)
    policy.delete()
    return redirect("list_policies")

def policy_list(request):
    policies = PolicyAnalysis.objects.all().order_by("-id")
    return render(request, "policyapp/policy_list.html", {"policies": policies})

def view_policy(request, pk):
    policy = get_object_or_404(PolicyAnalysis, pk=pk)
    return render(request, "policyapp/result.html", {
        "record_id": policy.id,
        "title": policy.title,
        "date_established": policy.date_established,
        "summary": policy.summary,
        "impacted_sectors": policy.impacted_sectors.split("\n"),
        "most_impacted_sector": policy.most_impacted_sector,
        "pdf_url": policy.pdf_file.url
    })