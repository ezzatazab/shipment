import os
from frappe import _
import frappe
from PIL import Image
from PyPDF2 import PdfMerger


@frappe.whitelist()
def download_related_docs(doctype, name):
    try:
        attachments_urls = []

        doc = frappe.get_doc(doctype, name)
        default_print_format = frappe.get_meta(doctype).default_print_format
        if not default_print_format:
            default_print_format = "Standard"
        if default_print_format:
            pdf_file = generate_pdf_with_print_format(doctype, name, default_print_format)
            attachments_urls.append(pdf_file)

        attachments = frappe.db.get_all(
            "File",
            filters={
                "attached_to_name": name,
                "attached_to_doctype": doctype
            },
            fields=["file_url"]
        )

        for attachment in attachments:
            if attachment.file_url.endswith(('.png', '.jpg', '.jpeg')):
                image_pdf = convert_image_to_pdf(attachment.file_url)
                attachments_urls.append(image_pdf)

            if attachment.file_url.endswith(('.pdf')):
                attachments_urls.append(attachment.file_url)

        if doctype == "Customs Shipment":
            for att in doc.get("cs_attachments"):
                if att.attachment_url.endswith(('.png', '.jpg', '.jpeg')):
                    image_pdf = convert_image_to_pdf(att.attachment_url)
                    if image_pdf not in attachments_urls:
                        attachments_urls.append(image_pdf)

                if att.attachment_url.endswith(('.pdf')):
                    if att.attachment_url not in attachments_urls:
                        attachments_urls.append(att.attachment_url)

        merger = PdfMerger()

        for pdf_url in attachments_urls:
            # More explicit path handling
            if pdf_url.startswith("/private/"):
                relative_path = pdf_url[9:]  # Remove "/private/" (9 characters)
                pdf_path = frappe.get_site_path("private", relative_path)
            elif pdf_url.startswith("/public/"):
                relative_path = pdf_url[8:]   # Remove "/public/" (8 characters)
                pdf_path = frappe.get_site_path("public", relative_path)
            elif pdf_url.startswith("/files/"):
                # Handle /files/ prefix - maps to public/files/
                relative_path = pdf_url[7:]  # Remove "/files/" (7 characters)
                pdf_path = frappe.get_site_path("public", "files", relative_path)
            else:
                # Handle URLs without prefix - try both private and public
                pdf_path = frappe.get_site_path("private", pdf_url.lstrip("/"))
                if not os.path.exists(pdf_path):
                    pdf_path = frappe.get_site_path("public", pdf_url.lstrip("/"))

            if not os.path.exists(pdf_path):
                frappe.msgprint(f"Attachment File not found: {pdf_path}", alert=True, indicator="red", realtime=True, title=_("Warning"))
                frappe.log_error(f"Attachment File not found: {pdf_path}", "Attachment Downloader")
                continue

            merger.append(pdf_path)

        output_filename = f"{name}_attachments.pdf"
        output_path = frappe.get_site_path("private", "files", output_filename)
        with open(output_path, "wb") as output_file:
            merger.write(output_file)

        # frappe.db.delete(
        #     "File",
        #     {
        #         "file_name": ["like", "%related_docs.pdf%"],
        #         "attached_to_doctype": doctype,
        #         "attached_to_name": name
        #     }
        # )

        with open(output_path, "rb") as merged_file:
            attached_file = frappe.get_doc({
                "doctype": "File",
                "file_name": output_filename,
                "is_private": 1,
                "content": merged_file.read()
            })
            attached_file.save()


        frappe.msgprint(_("Related documents downloaded successfully."), alert=True, indicator="green", realtime=True, title=_("Success")),

        frappe.db.commit()

        return attached_file.file_url
    
    except Exception as e:
        frappe.log_error(frappe.get_traceback(), "Error in downloading related documents")
        frappe.throw(_("An error occurred while downloading related documents: {0}").format(str(e)))


@frappe.whitelist()
def generate_pdf_with_print_format(doctype, name, format):
    doc = frappe.get_doc(doctype, name)
    frappe.local.lang = 'en'
    pdf_file = frappe.get_print(
        doctype, name, format, doc=doc, as_pdf=True
    )

    file_name = f"{name}.pdf"
    file_doc = frappe.get_doc({
        "doctype": "File",
        "file_name": file_name,
        "is_private": 1,
        "content": pdf_file
    })
    file_doc.save()

    return file_doc.file_url


def convert_image_to_pdf(image_url):
    """
    Convert an image file to a PDF file and return its relative file URL.
    """
    image_path = frappe.get_site_path("private", image_url.lstrip("/private/"))
    if not os.path.exists(image_path):
        image_path = frappe.get_site_path("public", image_url.lstrip("/public/"))
    if not os.path.exists(image_path):
        frappe.throw(f"Image not found: {image_path}")

    output_filename = image_url.split("/")[-1].rsplit(".", 1)[0] + "_temp.pdf"
    output_path = frappe.get_site_path("private", "files", output_filename)

    try:
        with Image.open(image_path) as img:
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            img.save(output_path, "PDF", resolution=100.0)
    except Exception as e:
        frappe.throw(f"Error converting image to PDF: {str(e)}")

    return f"/private/files/{output_filename}"