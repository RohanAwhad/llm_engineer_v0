from tui.llm_engineer import LLMEngineer


if __name__ == "__main__":
    import sys

    workspace = sys.argv[1]
    app = LLMEngineer(workspace)
    app.run()
