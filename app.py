from brain import Brain
from message import Message
import re
import argparse
from llm_engineer import get_input_from_user, llm_call

def save_composer_output(doc: str, filepath: str):
    """Saves the composer output to a specified file."""
    with open(filepath, 'w') as f:
        f.write(doc)
    print(f"Plan saved at: {filepath}")
    return filepath

def plan_composer():
    """Handles the process of composing a plan using user input and an LLM."""
    with open('prompts/composer_planner.txt', 'r') as f:
        sys_prompt = f.read()
    history = [Message('system', sys_prompt), ]

    user_turn = True
    try:
        while True:
            if user_turn:
                user_msg = get_input_from_user()  
                if user_msg.content:  
                    history.append(user_msg)  
                else:
                    print('No Input provided. Quitting ...')
                    raise KeyboardInterrupt

            print(f"\033[93m{history[-1]}\033[0m")
            llm_res = llm_call("gpt-4o-2024-08-06", history, temperature=0.8)
            print("\033[95m" + str(llm_res) + "\033[0m")

            history.append(Message('assistant', llm_res))
            user_turn = True
    except KeyboardInterrupt:
        if history[-1].role == 'assistant':
            llm_res = history[-1].content
            req_spec_doc_ptrn = re.compile(r'<\|REQ_SPEC_DOC_START\|>(.*?)<\|REQ_SPEC_DOC_END\|>', re.DOTALL)
            match = req_spec_doc_ptrn.search(llm_res)
            breakpoint()
            if match:
                doc = match.group(1).strip()
                if doc.startswith('```'): doc = ('\n'.join(doc.split('\n')[1:])).strip()
                if doc.endswith('```'): doc = ('\n'.join(doc.split('\n')[:-1])).strip()
                # Save the composed plan using default filename
                save_composer_output(doc, 'composer_plan.txt')
        exit(0)

def plan_executor(plan_filename: str, workspace: str):
    """Executes the plan specified in the given filename."""
    # TODO: (rohan): LLM will talk with brain here to create all the capable functions.
    pass

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process some arguments.')
    parser.add_argument('workspace', type=str, help='Workspace directory.')
    parser.add_argument('--plan_composer', action='store_true', help='Run the plan composer.')
    parser.add_argument('--plan_executor', type=str, default=None, help='Filepath for the plan executor.')
    args = parser.parse_args()

    workspace = args.workspace
    if args.plan_composer:
        plan_composer()
        # Assuming plan_composer function saves the output in 'composer_plan.txt'
        if args.plan_executor:
            save_path = args.plan_executor
        else:
            save_path = 'composer_plan.txt'
        # Saving plan output to the specified location
        save_composer_output('composer_plan.txt', save_path)

    if args.plan_executor:
        # Logic to load and execute plan_executor with the file content
        with open(args.plan_executor, 'r') as f:
            plan_content = f.read()
        plan_executor(args.plan_executor, workspace)

    if not args.plan_composer and not args.plan_executor:
        brain = Brain(workspace)
        while True:
            user_msg = get_input_from_user()
            if not user_msg.content: break
            brain.run(user_msg)
