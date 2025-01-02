import re

def replace_template_content(output_file, rendered_content):
    try:
        placeholder_comment = "<!-- comment for replacing rendered template content -->"
        with open(output_file, "r") as f:
            file_content = f.read()
        updated_content = re.sub(re.escape(placeholder_comment), rendered_content, file_content, count=1)

        with open("email/templateToPush/outtopush.html", "w") as f:
            f.write(updated_content)
        return 1
    except Exception as e:
        return 0

def render_email_template(template, email_data):
    output_file = "email/finalTemplate/baseout.html"
    try:
        start_marker = "(_start)"
        end_marker = "(_end)"
        start_index = template.find(start_marker)
        end_index = template.find(end_marker) + len(end_marker)
        if start_index == -1 or end_index == -1:
            return "Missing (_start) or (_end) in the template"

        dynamic_block = template[start_index + len(start_marker):end_index - len(end_marker)]
        rendered_blocks = ""
        for i, cve in enumerate(email_data):
            rendered_block = dynamic_block
            for placeholder, value in cve.items():
                rendered_block = rendered_block.replace(f"(.{placeholder})", str(value))
            if i == len(email_data) - 1:
                rendered_block = rendered_block.replace("<hr>", "")
            rendered_blocks += rendered_block
        final_template = template.replace(template[start_index:end_index], rendered_blocks)
        
        # print(final_template)
        final_render = replace_template_content(output_file, final_template)
        if not final_render:
            return "Something went wrong!"
        return "Successfully Generated!"    

    except Exception as e:
        print(e)
