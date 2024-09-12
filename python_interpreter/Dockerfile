FROM frolvlad/alpine-miniconda3

RUN mkdir /tmp/env
COPY python_interpreter_env.yaml /tmp/env/
RUN conda env create -f /tmp/env/python_interpreter_env.yaml
