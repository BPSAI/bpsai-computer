"""Computer SENSE/LEARN hooks for the dispatch orchestration loop.

These hooks were extracted from bpsai-framework to be owned by
Computer since they operate on Computer's domain data (portfolio,
signals, dispatch outcomes, status).
"""

from computer.hooks.briefing_reader import BriefingReader
from computer.hooks.dispatch_outcome_hook import DispatchOutcomeHook
from computer.hooks.next_sprint_hook import NextSprintHook
from computer.hooks.outcome_recorder import OutcomeRecorder
from computer.hooks.portfolio_reader import PortfolioStateReader
from computer.hooks.signal_closer import SignalCloser
from computer.hooks.signal_reader import SignalStoreReader
from computer.hooks.status_update_hook import StatusUpdateHook

__all__ = [
    "BriefingReader",
    "DispatchOutcomeHook",
    "NextSprintHook",
    "OutcomeRecorder",
    "PortfolioStateReader",
    "SignalCloser",
    "SignalStoreReader",
    "StatusUpdateHook",
]
