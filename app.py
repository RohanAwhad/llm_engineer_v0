import jinja2
from brain import Brain
from message import Message
import re
import argparse
from llm_functions import get_input_from_user, llm_call, summarize_conversation
from tui.llm_engineer import LLMEngineer
import os  # Importing os for file operations

def save_composer_output(doc: str, filepath: str) -> str:
    """Saves the composer output to a specified file."""
    with open(filepath, 'w') as f:
        f.write(doc)
    print(f"Plan saved at: {filepath}")
    return filepath

def plan_composer(save_path: str) -> None:
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
            if match:
                doc = match.group(1).strip()
                if doc.startswith('```'): doc = ('\n'.join(doc.split('\n')[1:])).strip()
                if doc.endswith('```'): doc = ('\n'.join(doc.split('\n')[:-1])).strip()
                # Save the composed plan using default filename
                save_composer_output(doc, save_path)

def plan_executor(plan_filename: str, workspace: str) -> None:
    """Executes the plan specified in the given filename."""
    
    # Load the system prompt as a Jinja template
    with open('prompts/composer_executor.txt', 'r') as f:
        template_content = f.read()
    template = jinja2.Template(template_content)

    # Initialize history as a list of Message objects
    history = []

    # Load the plan content
    with open(plan_filename, 'r') as plan_file:
        plan = plan_file.read()

    # Render the template with the plan
    rendered_prompt = template.render(requirement_specification_doc=plan)
    history.append(Message('system', rendered_prompt))
    history.append(Message('user', 'Hey there, Baby LLM here. What are we building today?'))

    brain = Brain(workspace)

    def convert_msg_for_brain(msg: Message) -> Message:
        """Converts a Message into a format suitable for the Brain."""
        baby_lm_content = re.compile(r'<\|BABY_LLM_CONVERSATION_START\|>(.*?)<\|BABY_LLM_CONVERSATION_END\|>', re.DOTALL)
        match = baby_lm_content.search(msg.content)
        if match:
            return Message('user', match.group(1).strip())
        else:
            return get_input_from_user()

    print('Starting execution ...')
    iter = 0
    while True:
        if len(history) > 10:
            summary = summarize_conversation("NousResearch/Hermes-3-Llama-3.1-405B-Turbo", history, provider='together')
            history = [history[0], Message('user', summary)] + history[-3:]

        # Use LLM to generate a message for the brain
        #llm_response = llm_call("claude-3-5-sonnet-20240620", history, temperature=0.8, provider='anthropic')
        #llm_response = llm_call("Qwen/Qwen2-72B-Instruct", history, temperature=0.8, provider='together')
        llm_response = llm_call("NousResearch/Hermes-3-Llama-3.1-405B-Turbo", history, temperature=0.8, provider='together', max_tokens=1024)
        print("COMPOSER MESSAGE")
        print(llm_response)

        history.append(Message('assistant', llm_response))

        # Check and log any log summary
        log_start_tag = "<|LOG_SUMMARY_START|>"
        log_end_tag = "<|LOG_SUMMARY_END|>"
        log_start_idx = llm_response.find(log_start_tag)
        log_end_idx = llm_response.find(log_end_tag)
        
        if log_start_idx != -1 and log_end_idx != -1:
            log_content = llm_response[log_start_idx + len(log_start_tag):log_end_idx].strip()
            with open('log.txt', 'a') as log_file:
                log_file.write(log_content + "\n")

        # Check for the job finish tag
        if "<|JOB_FINISH|>" in llm_response:
            break

        # Send the last message to the brain and get the response
        brain_output = brain.run(convert_msg_for_brain(history[-1]))
        if not brain_output: brain_output = '<NO MESSAGE FROM USER. INITIATE CONVERSATION>'
        user_message = Message('user', brain_output)
        history.append(user_message)
        iter += 1
        if iter % 10 == 0:
            print('Iteration:', iter)
            input('Press Enter to continue')

    print("Plan execution completed.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Process some arguments.')
    parser.add_argument('workspace', type=str, help='Workspace directory.')
    parser.add_argument('--tui', action='store_true', help='Chat with brain in TUI mode.')
    parser.add_argument('--plan_composer', action='store_true', help='Run the plan composer.')
    parser.add_argument('--plan_executor', type=str, default=None, help='Filepath for the plan executor.')
    parser.add_argument('--use_previous_context', action='store_true', help='Use previous context or start fresh.')

    args = parser.parse_args()
    workspace = args.workspace

    # Remove previous context files if not using previous context
    if not args.use_previous_context:
        history_file = os.path.join(workspace, '.brain_history')
        message_list_file = os.path.join(workspace, '.brain_message_list')
        if os.path.exists(history_file):
            os.remove(history_file)
        if os.path.exists(message_list_file):
            os.remove(message_list_file)

    if args.plan_composer:
        # Assuming plan_composer function saves the output in 'composer_plan.txt'
        if args.plan_executor:
            save_path = args.plan_executor
        else:
            save_path = 'composer_plan.txt'
        plan_composer(save_path)

    if args.plan_executor:
        # Logic to load and execute plan_executor with the file content
        with open(args.plan_executor, 'r') as f:
            plan_content = f.read()
        plan_executor(args.plan_executor, workspace)
    elif args.tui:
        LLMEngineer(workspace).run()
        exit(0)
    else:
        brain = Brain(workspace)
        while True:
            user_msg = get_input_from_user()
            if not user_msg.content: break
            brain.run(user_msg)
