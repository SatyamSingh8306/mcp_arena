import sys
import types


try:
    import jira  # noqa: F401
except ImportError:
    try:
        from atlassian import Jira as _Jira

        _jira_mod = types.ModuleType("jira")
        _jira_mod.JIRA = _Jira
        sys.modules.setdefault("jira", _jira_mod)
    except ImportError:
        pass
