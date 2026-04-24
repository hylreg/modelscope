import os
from typing import Iterable

import dspy
from dspy.teleprompt import BootstrapFewShot


def _require_env() -> tuple[str, str]:
    api_base = os.getenv("MODELSCOPE_API_BASE", "https://api-inference.modelscope.cn/v1")
    model = os.getenv("MODELSCOPE_MODEL", "Qwen/Qwen3.5-397B-A17B")
    if not os.getenv("OPENAI_API_KEY"):
        raise RuntimeError(
            "未检测到 OPENAI_API_KEY。请把 ModelScope Token 放到环境变量，例如：\n"
            "export OPENAI_API_KEY='ms-xxxx'\n"
        )
    return api_base, model


class QA(dspy.Signature):
    question: str = dspy.InputField()
    answer: str = dspy.OutputField(desc="尽量简短、精确的答案")


class QAModule(dspy.Module):
    def __init__(self) -> None:
        super().__init__()
        self.predict = dspy.Predict(QA)

    def forward(self, question: str) -> dspy.Prediction:
        return self.predict(question=question)


def exact_match_metric(example: dspy.Example, pred: dspy.Prediction, _trace=None) -> bool:
    gold = str(example.answer).strip()
    got = str(pred.answer).strip()
    return got == gold


def evaluate(program: dspy.Module, devset: Iterable[dspy.Example]) -> tuple[int, int]:
    ok = 0
    total = 0
    for ex in devset:
        total += 1
        pred = program(question=ex.question)
        if exact_match_metric(ex, pred):
            ok += 1
    return ok, total


def main() -> None:
    api_base, model = _require_env()

    lm = dspy.LM(
        f"openai/{model}",
        api_base=api_base,
        model_type="chat",
        temperature=0.0,
        max_tokens=128,
    )
    dspy.configure(lm=lm)

    # 这组任务故意设计成“需要对输出格式强约束”，以便 few-shot 优化的提升更明显。
    # 目标：输出必须完全匹配 gold answer（严格评测）。
    trainset = [
        dspy.Example(question="把 7 写成二进制", answer="111").with_inputs("question"),
        dspy.Example(question="把 10 写成二进制", answer="1010").with_inputs("question"),
        dspy.Example(question="把 13 写成二进制", answer="1101").with_inputs("question"),
        dspy.Example(question="把 16 写成二进制", answer="10000").with_inputs("question"),
    ]
    devset = [
        dspy.Example(question="把 9 写成二进制", answer="1001").with_inputs("question"),
        dspy.Example(question="把 12 写成二进制", answer="1100").with_inputs("question"),
        dspy.Example(question="把 15 写成二进制", answer="1111").with_inputs("question"),
        dspy.Example(question="把 18 写成二进制", answer="10010").with_inputs("question"),
    ]

    base = QAModule()
    ok0, total0 = evaluate(base, devset)
    print(f"优化前：{ok0}/{total0} exact-match")

    # 编译（提示词/示例自动优化）：BootstrapFewShot 会为 Predict 自动挑选/构造 demos。
    teleprompter = BootstrapFewShot(metric=exact_match_metric, max_bootstrapped_demos=4, max_labeled_demos=4)
    optimized = teleprompter.compile(base, trainset=trainset)

    ok1, total1 = evaluate(optimized, devset)
    print(f"优化后：{ok1}/{total1} exact-match")

    # 展示优化后的“提示中 few-shot demos”（便于直观看到优化结果）
    try:
        # dspy 3.x: predictor 里会有 demos（结构可能随版本变化，所以做容错）
        demos = getattr(getattr(optimized, "predict", None), "demos", None)
        if demos:
            print("\n优化得到的 demos（节选）:")
            for i, d in enumerate(demos[:4], start=1):
                print(f"- demo#{i} Q={d.question!r} A={d.answer!r}")
    except Exception:
        pass


if __name__ == "__main__":
    main()

