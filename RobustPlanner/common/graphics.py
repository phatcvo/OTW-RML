from __future__ import division, print_function

from RobustPlanner import agents
# from RobustPlanner.agents.robust.constrained_epc import ConstrainedEPCAgent
# from RobustPlanner.agents.robust.graphics.constrained_epc_graphics import ConstrainedEPCGraphics
# from RobustPlanner.agents.robust.graphics.robust_graphics import DiscreteRobustPlannerGraphics, IntervalRobustPlannerGraphics
# from RobustPlanner.agents.robust.graphics.robust_epc_graphics import RobustEPCGraphics
# from RobustPlanner.agents.robust.robust import DiscreteRobustPlannerAgent, IntervalRobustPlannerAgent
# from RobustPlanner.agents.robust.robust_epc import RobustEPCAgent

# from RobustPlanner.agents.tree_search.abstract import AbstractTreeSearchAgent
# from RobustPlanner.agents.tree_search.graphics import TreeGraphics

# Graphical visualization of any Agent implementing AbstractAgent.
class AgentGraphics(object):

    @classmethod
    def display(cls, agent, agent_surface, sim_surface=None):        
        if isinstance(agent, agents.robust.robust.IntervalRobustPlannerAgent):
            agents.robust.graphics.robust_graphics.IntervalRobustPlannerGraphics.display(agent, agent_surface, sim_surface)
        elif isinstance(agent, agents.robust.robust.DiscreteRobustPlannerAgent):
            agents.robust.graphics.robust_graphics.DiscreteRobustPlannerGraphics.display(agent, agent_surface, sim_surface)
        elif isinstance(agent, agents.robust.constrained_epc.ConstrainedEPCAgent):
            agents.robust.graphics.constrained_epc_graphics.ConstrainedEPCGraphics.display(agent, agent_surface, sim_surface)
        elif isinstance(agent, agents.robust.robust_epc.RobustEPCAgent):
            agents.robust.graphics.robust_epc_graphics.RobustEPCGraphics.display(agent, agent_surface, sim_surface)
        elif isinstance(agent, agents.tree_search.abstract.AbstractTreeSearchAgent):
            agents.tree_search.graphics.TreeGraphics.display(agent, agent_surface)
