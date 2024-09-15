from brain import Brain


if __name__ == "__main__":
    import sys

    workspace = sys.argv[1]
    brain = Brain(workspace)
    brain.run()
