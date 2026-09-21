import html

# Dev A's frontend (task-report-preview.tsx) deliberately mirrors this
# exact HTML/CSS token-for-token so the live preview matches the real
# screenshot. Do not restyle this without updating that component too.
_TERMINAL_OUTPUT_CHAR_LIMIT = 2000


def render_terminal_html(output: str) -> str:
    """Renders `output` as a dark terminal window, matching
    task-report-preview.tsx's TerminalWindow component exactly."""
    safe_output = (
        output[:_TERMINAL_OUTPUT_CHAR_LIMIT] + "\n...[Output Truncated]"
        if len(output) > _TERMINAL_OUTPUT_CHAR_LIMIT
        else output
    )

    return f"""
    <!DOCTYPE html>
    <html>
      <head>
        <style>
          body {{ background: transparent; margin: 0; padding: 20px; display: inline-block; }}
          .terminal-window {{ background-color: #1e1e1e; border-radius: 8px; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.4); overflow: hidden; font-family: 'Courier New', Courier, monospace; min-width: 400px; max-width: 800px; }}
          .terminal-header {{ background-color: #2d2d2d; padding: 10px 12px; display: flex; gap: 8px; }}
          .dot {{ width: 12px; height: 12px; border-radius: 50%; }}
          .dot.red {{ background-color: #ff5f56; }}
          .dot.yellow {{ background-color: #ffbd2e; }}
          .dot.green {{ background-color: #27c93f; }}
          .terminal-body {{ padding: 16px; color: #d4d4d4; font-size: 14px; line-height: 1.5; white-space: pre-wrap; word-wrap: break-word; }}
        </style>
      </head>
      <body>
        <div class="terminal-window" id="terminal">
          <div class="terminal-header">
            <div class="dot red"></div><div class="dot yellow"></div><div class="dot green"></div>
          </div>
          <div class="terminal-body">{html.escape(safe_output)}</div>
        </div>
      </body>
    </html>
    """
