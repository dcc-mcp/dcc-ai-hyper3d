"""download_assets skill entry point."""

from _hyper3d import download_assets as operation, tool_call


def main(task_uuid, subscription_key, output_dir, filenames=None):
    return tool_call(operation, task_uuid=task_uuid, subscription_key=subscription_key, output_dir=output_dir, filenames=filenames)


if __name__ == "__main__":
    from dcc_mcp_core.skills_helper import run_main
    run_main(main)
