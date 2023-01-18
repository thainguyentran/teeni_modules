# repo of modules that i have done for Teeni project, which include OCR

For this project, the OCR will read from the PDF file based on the templates that have been created.</br>
to use these templates, please add these two lines to the end of odoo's config file (usually) *odoo.conf*:<br>
<code>invoice2data_templates_dir = /mnt/extra-addons/ocr/invoice2data_local_templates
invoice2data_exclude_built_in_templates = True
</code>

Also, it use invoice2data library, but for the module sale_order_import to work, the version required is <strong>0.3.5</strong></br>
All the external dependencies are put in */teeni/requirements.txt*</br>
If there is any bugs or problems, please do not hesitate to contact me, I am happy to debug and correct it.</br>
my email: <thainguyentran@icloud.com></br>
Or you can comment directly on the line of code that have problem.
