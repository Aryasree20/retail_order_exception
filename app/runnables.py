"""Use LangChain Core runnables when installed; tiny compatible fallback for offline tests."""
try:
    from langchain_core.runnables import RunnableLambda, RunnableParallel, RunnableBranch
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    class _Pipe:
        def __init__(self, fn): self.fn=fn
        def invoke(self, value): return self.fn(value)
        def __or__(self, other): return _Pipe(lambda value: other.invoke(self.invoke(value)))
    class RunnableLambda(_Pipe):
        def __init__(self, fn): super().__init__(fn)
    class RunnableParallel(_Pipe):
        def __init__(self, **steps): super().__init__(lambda value: {k:v.invoke(value) if hasattr(v,'invoke') else v(value) for k,v in steps.items()})
    class RunnableBranch(_Pipe):
        def __init__(self, *branches):
            def choose(value):
                for condition, runnable in branches[:-1]:
                    if condition(value): return runnable.invoke(value)
                last=branches[-1]
                return last.invoke(value) if hasattr(last,'invoke') else last(value)
            super().__init__(choose)
