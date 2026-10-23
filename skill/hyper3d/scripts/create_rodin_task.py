"""create_rodin_task skill entry point."""

from _hyper3d import create_rodin_task as operation, tool_call


def main(parameters=None, image_paths=None):
    return tool_call(operation, parameters=parameters, image_paths=image_paths)


if __name__ == "__main__":
    from dcc_mcp_core.skills_helper import run_main
    run_main(main)
