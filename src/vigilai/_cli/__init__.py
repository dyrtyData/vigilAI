import typer
from inspect_ai._util.dotenv import init_dotenv

from vigilai._cli.eval import eval_command
from vigilai._cli.list import list_command
from vigilai._cli.report import report_command


app = typer.Typer(
    rich_markup_mode="markdown",
    help=(
        "**vigilAI** — Brazil PL 2338/2023 compliance evaluation for Generative AI. "
        "Forked from the [COMPL-AI](https://compl-ai.org) EU AI Act framework "
        "(ETH Zurich / INSAIT / LatticeFlow AI) and built on "
        "[Inspect AI](https://inspect.aisi.org.uk/)."
    ),
)

app.command("eval")(eval_command)
app.command("list")(list_command)
app.command("report")(report_command)


def main() -> None:
    init_dotenv()
    app()


if __name__ == "__main__":
    main()
