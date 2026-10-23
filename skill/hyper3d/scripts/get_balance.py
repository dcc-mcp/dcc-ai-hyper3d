"""get_balance skill entry point."""

from _hyper3d import get_balance as operation, tool_call


def main(usage_page=None):
    return tool_call(operation, usage_page=usage_page)


if __name__ == "__main__":
    from dcc_mcp_core.skills_helper import run_main
    run_main(main)
