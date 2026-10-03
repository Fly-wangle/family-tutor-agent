#!/usr/bin/env python3
"""Create a new private tutor workspace from the shipped public template."""

import argparse
from pathlib import Path
import shutil
import tempfile


TEMPLATE_ROOT = Path(__file__).resolve().parents[1]
TEMPLATE_FILES = (
    "AGENTS.md", "LICENSE", "PRIVACY.md", "docs/setup.md", "docs/tts.md",
    "knowledge-base/README.md", "knowledge-base/data_structure.md",
    "knowledge-base/student-profile.md", "knowledge-base/thread-policy.md",
    "knowledge-base/tutoring-playbook.md", "knowledge-base/ingest-protocol.md",
    "knowledge-base/source-register.md", "knowledge-base/resources-to-add.md",
    "knowledge-base/question-log.md", "knowledge-base/log.md",
    "knowledge-base/learner/student-learning-profile.md",
    "knowledge-base/learner/subject-weakness-map.md",
    "knowledge-base/learner/learning-rubric.md", "knowledge-base/reports/latest.md",
    "knowledge-base/curriculum/README.md", "knowledge-base/curriculum/math.md",
    "knowledge-base/curriculum/chinese.md", "knowledge-base/curriculum/english.md",
    "knowledge-base/curriculum/science.md", "knowledge-base/subjects/math.md",
    "knowledge-base/subjects/chinese.md", "knowledge-base/subjects/english.md",
    "knowledge-base/subjects/science.md", "knowledge-base/exams/README.md",
    "knowledge-base/exams/exam-calendar.md", "knowledge-base/exams/review-playbook.md",
    "knowledge-base/integrations/README.md",
    "knowledge-base/integrations/oral-session-brief.md",
    "knowledge-base/methods/math-progression.md",
    "knowledge-base/methods/english-news.md", "knowledge-base/methods/dictation.md",
    "knowledge-base/methods/oral-teaching.md", "knowledge-base/methods/review-loop.md",
)

WORKSPACE_README = """# 家庭辅导老师私有工作区

此目录是空的家庭工作区，不包含任何孩子的历史记录，也尚未部署语音或自动化。

1. 在 Agent 中打开本目录，填写 [学生档案](knowledge-base/student-profile.md)。
2. 建立家长管理、分科学生与固定复盘线程，在 [线程分工](knowledge-base/thread-policy.md) 登记私有入口。
3. 按 [安装与验收](docs/setup.md) 核对规则读取、教材进度和文字教学，再单独配置和试听语音。
4. 原始资料放 materials，按 [归档协议](knowledge-base/ingest-protocol.md) 整理。
5. [最新复盘](knowledge-base/reports/latest.md) 初始为空，只从真实输出形成递进卡。

默认 .gitignore 忽略全部文件，防止误提交真实资料。不要将本目录推送到公开仓库；
需版本管理时由家长另建私有仓库并审阅忽略规则。更新规则时保留真实档案和学情，不整目录覆盖。
"""


def create_workspace(destination: Path, template_root: Path = TEMPLATE_ROOT) -> Path:
    root = template_root.resolve()
    raw_destination = destination.expanduser().absolute()
    if raw_destination.is_symlink():
        raise ValueError("目标不能是符号链接，请选择一个明确的新目录。")
    target = raw_destination.resolve()
    if target == root or root in target.parents:
        raise ValueError("目标必须在公开模板目录之外，不能在公开仓库填写真实资料。")
    if target.exists() and (not target.is_dir() or any(target.iterdir())):
        raise ValueError("目标已存在且不为空，未覆盖任何文件；请选择新目录。")

    sources = []
    for relative in TEMPLATE_FILES:
        source = root / relative
        # Only named shipped files are copied; never follow source symlinks.
        chain = [source, *list(source.parents)[:len(Path(relative).parts) - 1]]
        if any(item.is_symlink() for item in chain):
            raise ValueError(f"模板文件或目录不能是符号链接：{relative}")
        if not source.is_file():
            raise ValueError(f"模板不完整，缺少：{relative}")
        sources.append((relative, source))

    target.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=".family-tutor-init-", dir=target.parent) as temp:
        staged = Path(temp) / "workspace"
        staged.mkdir()
        for relative, source in sources:
            output = staged / relative
            output.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(source, output)
        (staged / "README.md").write_text(WORKSPACE_README, encoding="utf-8")
        (staged / ".gitignore").write_text("# Private workspace: ignore all files by default.\n*\n", encoding="utf-8")
        (staged / "materials").mkdir()
        (staged / "materials/README.md").write_text(
            "# 私有原始资料\n\n教材、老师通知、图片与音频放这里，不上传公开仓库。\n",
            encoding="utf-8",
        )
        # rmdir refuses nonempty targets, including files added during preparation.
        if target.exists():
            target.rmdir()
        staged.rename(target)
    return target


def main() -> None:
    parser = argparse.ArgumentParser(description="创建独立的私有家庭辅导工作区，不覆盖旧资料。")
    parser.add_argument("--dest", type=Path, required=True, help="模板目录以外的新目录或空目录")
    args = parser.parse_args()
    try:
        result = create_workspace(args.dest)
    except (ValueError, OSError) as error:
        parser.exit(1, f"未完成初始化：{error}\n")
    print(f"已创建空工作区：{result}")
    print("下一步：填写学生档案、手动建立线程，再分别验收文字与语音。")
    print("尚未安装客户端、语音引擎或自动化；未导入任何孩子的学习记录。")


if __name__ == "__main__":
    main()
