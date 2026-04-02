import argparse
import os
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET
from pathlib import Path

import requests
from dotenv import load_dotenv


load_dotenv(Path(__file__).resolve().parent / ".env")


def _extract_namespace(tag: str) -> str:
    if tag.startswith("{") and "}" in tag:
        return tag.split("}", 1)[0] + "}"
    return ""


def _text(node, path: str, default: str = "") -> str:
    found = node.find(path)
    if found is None or found.text is None:
        return default
    return found.text.strip()


def _parameter_defaults(root: ET.Element) -> dict[str, str]:
    defaults: dict[str, str] = {}
    for parameter in root.findall("./properties/hudson.model.ParametersDefinitionProperty/parameterDefinitions/*"):
        name = _text(parameter, "name")
        if not name:
            continue
        default_value = _text(parameter, "defaultValue")
        if not default_value:
            choices = parameter.findall("./choices/a/string")
            if choices and choices[0].text:
                default_value = choices[0].text.strip()
        defaults[name] = default_value
    return defaults


def _fallback_context(defaults: dict[str, str]) -> dict[str, str]:
    context = dict(defaults)
    context.update({key: value for key, value in os.environ.items() if value})
    if "GITLAB_SERVER" not in context:
        gitlab_url = os.environ.get("GITLAB_URL", "").strip()
        if gitlab_url:
            parsed = urllib.parse.urlparse(gitlab_url)
            if parsed.netloc:
                context["GITLAB_SERVER"] = parsed.netloc
    if "BUILD_LIB_BRANCH" not in context:
        context["BUILD_LIB_BRANCH"] = "master"
    if "REPO_BRANCH" not in context:
        context["REPO_BRANCH"] = "master"
    return context


def _resolve_placeholders(value: str, context: dict[str, str]) -> str:
    pattern = re.compile(r"\$\{([^}]+)\}")

    def replace(match: re.Match[str]) -> str:
        key = match.group(1)
        return context.get(key, match.group(0))

    return pattern.sub(replace, value)


def extract_pipeline_scm(xml_path: Path) -> dict[str, str] | None:
    tree = ET.parse(xml_path)
    root = tree.getroot()
    if root.tag != "flow-definition":
        return None

    definition = root.find("definition")
    if definition is None or definition.attrib.get("class") != "org.jenkinsci.plugins.workflow.cps.CpsScmFlowDefinition":
        return None

    scm = definition.find("scm")
    if scm is None:
        return None

    remote = scm.find("./userRemoteConfigs/hudson.plugins.git.UserRemoteConfig")
    branch = scm.find("./branches/hudson.plugins.git.BranchSpec/name")
    script_path = definition.find("scriptPath")

    if remote is None or branch is None or script_path is None:
        return None

    defaults = _parameter_defaults(root)
    context = _fallback_context(defaults)

    repo_url = _resolve_placeholders(_text(remote, "url"), context)
    credentials_id = _text(remote, "credentialsId")
    branch_name = _resolve_placeholders(branch.text.strip().replace("*/", ""), context) if branch.text else "master"
    path = _resolve_placeholders(script_path.text.strip(), context) if script_path.text else "Jenkinsfile"

    return {
        "repo_url": repo_url,
        "branch": branch_name,
        "script_path": path,
        "credentials_id": credentials_id,
    }


def _project_api_path(repo_url: str) -> tuple[str, str]:
    parsed = urllib.parse.urlparse(repo_url)
    project_path = parsed.path.lstrip("/")
    if project_path.endswith(".git"):
        project_path = project_path[:-4]
    host = f"{parsed.scheme}://{parsed.netloc}"
    return host, project_path


def fetch_jenkinsfile(xml_path: Path, token: str) -> tuple[dict[str, str], str]:
    scm = extract_pipeline_scm(xml_path)
    if not scm:
        raise ValueError(f"No CpsScmFlowDefinition found in {xml_path}")

    host, project_path = _project_api_path(scm["repo_url"])
    project_id = urllib.parse.quote(project_path, safe="")
    file_path = urllib.parse.quote(scm["script_path"], safe="")
    url = f"{host}/api/v4/projects/{project_id}/repository/files/{file_path}/raw?ref={urllib.parse.quote(scm['branch'], safe='')}"

    response = requests.get(
        url,
        headers={"PRIVATE-TOKEN": token},
        timeout=180,
    )
    response.raise_for_status()
    return scm, response.text


def main() -> int:
    parser = argparse.ArgumentParser(description="Fetch Jenkinsfile referenced by a Jenkins XML pipeline job.")
    parser.add_argument("xml_path", help="Path to the Jenkins XML config file.")
    parser.add_argument("--token", help="GitLab token. If omitted, reads GITLAB_USER_TOKEN or GITLAB_TOKEN.")
    parser.add_argument("--output", help="Optional file path to save the Jenkinsfile content.")
    args = parser.parse_args()

    token = args.token or os.environ.get("GITLAB_USER_TOKEN") or os.environ.get("GITLAB_TOKEN")
    if not token:
        raise SystemExit("Missing token. Provide --token or set GITLAB_USER_TOKEN / GITLAB_TOKEN.")

    scm, content = fetch_jenkinsfile(Path(args.xml_path), token)
    print(f"Fetched {scm['script_path']} from {scm['repo_url']} @ {scm['branch']}")
    if args.output:
        Path(args.output).write_text(content, encoding="utf-8")
    else:
        print(content)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())