"""get_download_links skill entry point."""

from _hyper3d import get_download_links as operation, tool_call


def main(task_uuid):
    return tool_call(operation, task_uuid=task_uuid)


if __name__ == "__main__":
    from dcc_mcp_core.skills_helper import run_main
    run_main(main)
