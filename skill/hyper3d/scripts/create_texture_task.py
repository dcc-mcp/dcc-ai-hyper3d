"""create_texture_task skill entry point."""

from _hyper3d import create_texture_task as operation, tool_call


def main(parameters=None, model_path=None, image_paths=None):
    return tool_call(operation, parameters=parameters, model_path=model_path, image_paths=image_paths)


if __name__ == "__main__":
    from dcc_mcp_core.skills_helper import run_main
    run_main(main)
