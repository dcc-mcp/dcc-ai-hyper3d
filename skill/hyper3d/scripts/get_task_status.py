"""get_task_status skill entry point."""

from _hyper3d import get_task_status as operation, tool_call


def main(subscription_key):
    return tool_call(operation, subscription_key=subscription_key)


if __name__ == "__main__":
    from dcc_mcp_core.skills_helper import run_main
    run_main(main)
