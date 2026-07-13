import sys
from typing import AsyncGenerator, Any

from rich.console import Console
from rich.live import Live
from rich.markdown import Markdown
from rich.panel import Panel
from rich.prompt import Prompt
from rich.theme import Theme

class RichUI:
    def __init__(self, no_rich: bool = False):
        self.no_rich = no_rich
        # Determine if we should really use Rich based on TTY and flag
        # If no_rich is False, but stdout is not a TTY, we might want to disable Rich
        # unless forced (Rich usually auto-detects, but Live display can be messy in non-TTY)
        self.use_rich = not no_rich and sys.stdout.isatty()

        if self.use_rich:
            self.theme = Theme({
                "header": "bold purple",
                "status": "bold orange1",
                "prompt": "bold orange1",
                "panel.border": "purple",
                "panel.title": "bold purple",
            })
            self.console = Console(theme=self.theme)
        else:
            self.console = None

    def print_banner(self, text: str):
        if self.use_rich:
            self.console.print(Panel(f"[header]{text}[/]", border_style="panel.border"))
        else:
            print(text)
            print("=" * len(text))

    def print_status(self, text: str):
        if self.use_rich:
            self.console.print(f"[status]{text}[/]")
        else:
            print(text)

    def print_error(self, text: str):
        if self.use_rich:
            self.console.print(f"[bold red]Error: {text}[/]")
        else:
            print(f"Error: {text}")

    def ask_user(self, prompt_text: str = "\nUser> ") -> str:
        """
        Prompts the user for input.
        """
        if self.use_rich:
            # Styled prompt
            # We strip the newline from the beginning if present because Prompt.ask handles its own spacing usually,
            # but strict replication of the old prompt "\nUser> " implies a newline before.
            if prompt_text.startswith("\n"):
                self.console.print()
                prompt_text = prompt_text[1:]

            # Add style tags
            styled_prompt = f"[prompt]{prompt_text}[/]"
            return Prompt.ask(styled_prompt, console=self.console)
        else:
            return input(prompt_text)

    async def stream_response(self, event_stream: AsyncGenerator[Any, None], title: str = "Coordinator"):
        """
        Streams the response from the agent.
        """
        if not self.use_rich:
            print(f"{title}> ", end="", flush=True)
            async for event in event_stream:
                if isinstance(event, str):
                    print(event, end="", flush=True)
                elif event.content:
                    if hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if part.text:
                                print(part.text, end="", flush=True)
                    else:
                        print(event.content, end="", flush=True)
            print() # Newline
            return

        # Rich mode
        accumulated_text = ""
        markdown = Markdown(accumulated_text)

        # Initial panel
        panel = Panel(
            markdown,
            title=f"[panel.title]{title}[/]",
            border_style="panel.border",
            subtitle="[dim]Streaming...[/]"
        )

        with Live(panel, console=self.console, refresh_per_second=10) as live:
            async for event in event_stream:
                chunk = ""
                if isinstance(event, str):
                    chunk += event
                elif event.content:
                    if hasattr(event.content, 'parts'):
                        for part in event.content.parts:
                            if part.text:
                                chunk += part.text
                    else:
                        # Fallback for simple content
                        chunk += str(event.content)

                if chunk:
                    accumulated_text += chunk
                    # Update the panel with new markdown
                    # We create a new Markdown object because it parses the full text
                    live.update(Panel(
                        Markdown(accumulated_text),
                        title=f"[panel.title]{title}[/]",
                        border_style="panel.border",
                        subtitle="[dim]Streaming...[/]"
                    ))

            # Final update to remove subtitle or show done
            live.update(Panel(
                Markdown(accumulated_text),
                title=f"[panel.title]{title}[/]",
                border_style="panel.border",
                subtitle=""
            ))

