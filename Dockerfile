FROM public.ecr.aws/lambda/python:3.12

COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r requirements.txt

COPY nhcx/ ${LAMBDA_TASK_ROOT}/nhcx/

# Two entrypoints share this one image (§4/§5 guidelines: one image per module):
#   nhcx.main.handler      — API Gateway -> FastAPI (sender + receiver ack)
#   nhcx.consumer.handler  — SQS -> decrypt/store worker
CMD ["nhcx.main.handler"]
