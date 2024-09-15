from brain import Brain
from message import Message
import re
from llm_engineer import get_input_from_user, llm_call

def plan_composer():
    with open('prompts/composer_planner.txt', 'r') as f: sys_prompt = f.read()
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
                with open('composer_plan.txt', 'w') as f:
                    f.write(doc)
        exit(0)


def plan_executor(plan_filename: str, workspace: str):
    # TODO: (rohan): LLM will talk with brain here to create all the capable functions.:w
    pass

if __name__ == "__main__":
    import sys

    workspace = sys.argv[1]
    brain = Brain(workspace)
    while True:
        user_msg = get_input_from_user()
        if not user_msg.content: break
        brain.run(user_msg)
