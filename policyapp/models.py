from django.db import models

class PolicyAnalysis(models.Model):
    title = models.CharField(max_length=255)
    date_established = models.CharField(max_length=100)
    summary = models.TextField()
    impacted_sectors = models.TextField()
    most_impacted_sector = models.TextField()
    pdf_file = models.FileField(upload_to='pdfs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title
