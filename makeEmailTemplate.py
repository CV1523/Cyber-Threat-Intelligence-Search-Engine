import os

output_file_path = 'email/templates/toPush/index.html'

def generate_EmailTemplate(cve_details):
    with open('email/templates/base.html', 'r', encoding='utf-8') as file:
        template = file.read()

    cve_entries = ""

    for index, cve in enumerate(cve_details):
        cve_entry = f"""
            <div id="emailBody">
                <h2 class="cve-title" style="font-weight: bold;">
                    {cve['cve_name']}
                </h2>
                <div class="cve-description" style="margin-top: 10px;
            padding: 5px;">
                    <div class="cve-table">
                        <table class="center" style="padding: 10px; 
            border-collapse: collapse; margin-left: auto;
            margin-right: auto;">
                            <thead>
                                <th style="text-align: center;
                                padding: 6px;
                                border: 1px solid black;
                                border-collapse: collapse;">CVE NUMBER</th>
                                <th style="text-align: center;
                                padding: 6px;
                                border: 1px solid black;
                                border-collapse: collapse;">SEVERITY</th>
                            </thead>
                            <tbody>
                                <tr style="text-align: center;
                                padding: 6px;
                                border: 1px solid black;
                                border-collapse: collapse;">
                                    <td style="text-align: center;
                                padding: 6px;
                                border: 1px solid black;
                                border-collapse: collapse;">{cve['cve_number']}</td>
                                    <td style="text-align: center;
                                padding: 6px;
                                border: 1px solid black;
                                border-collapse: collapse;">{cve['cve_severity']}/10</td>
                                </tr>
                            </tbody>
                        </table>
                    </div>
                    <div class="cve-actualdesc" style="margin-top: 10px;">
                        <p style="text-align: justify; text-justify: inter-word;">
                            &ensp;{cve['cve_description']}
                        </p>
                        <div class="cve-pubDate" style="margin-top: 30px;">
                            <p>
                                <strong>Published Date:</strong>  {cve['cve_pubdate']}
                            </p>
                        </div>
                    </div>
                </div>
            </div>
            """
        
        if index < len(cve_details) - 1:
            cve_entry += """
            <div class="horizontal-line" style="width: 100%;
            display: block;">
                <hr style="border-width: 1px;">
            </div>
            """
        
        cve_entries += cve_entry

    updated_html = template.replace('<!-- CVE_ENTRIES_PLACEHOLDER -->', cve_entries)

    with open(output_file_path, 'w', encoding='utf-8') as output_file:
        output_file.write(updated_html)

    print(f"\nGenerated Template into: {output_file_path}")

if __name__ == "__main__":
    script_dir = os.path.dirname(os.path.realpath(__file__))
    os.chdir(script_dir)

# Example usage
# cve_details = [
#     {
#         'cve_name': 'Octopus Server Improper Access Control',
#         'cve_number': 'CVE-2024-4811',
#         'cve_severity': '2.2',
#         'cve_description': 'In affected versions of Octopus Server under certain conditions, a user with specific role assignments can access restricted project artifacts.',
#         'cve_pubdate': 'Thu, 25 Jul 2024 05:15:26 +0000'
#     },
#     {
#         'cve_name': 'GitLab CE/EE Artifact Information Disclosure',
#         'cve_number': 'CVE-2024-7057',
#         'cve_severity': '4.3',
#         'cve_description': 'An information disclosure vulnerability in GitLab CE/EE affecting all versions starting from 16.7 prior to 17.0.5, starting from 17.1 prior to 17.1.3, and starting from 17.2 prior to 17.2.1 where job artifacts can be inappropriately exposed to users lacking the proper authorization level.',
#         'cve_pubdate': 'Thu, 25 Jul 2024 01:15:10 +0000'
#     }
# ]
# generate_EmailTemplate(cve_details)