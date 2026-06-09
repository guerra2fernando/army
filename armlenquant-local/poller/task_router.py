"""
Task Router
Routes tasks to the appropriate agent for execution.
"""
from typing import Dict, Optional
from loguru import logger

from agents.base_agent import BaseAgent, AgentResult


class TaskRouter:
    """
    Routes tasks to registered agents.
    """
    
    def __init__(self):
        self._agents: Dict[str, BaseAgent] = {}
        self.logger = logger.bind(component="router")
    
    def register_agent(self, agent_type: str, agent: BaseAgent):
        """
        Register an agent for a specific task type.
        
        Args:
            agent_type: The agent target type (e.g., "JOB_HUNTER")
            agent: The agent instance
        """
        self._agents[agent_type] = agent
        self.logger.info(f"Registered agent: {agent_type} -> {agent.name}")
    
    def get_agent(self, agent_type: str) -> Optional[BaseAgent]:
        """Get agent for a specific type."""
        return self._agents.get(agent_type)
    
    def get_registered_types(self) -> list:
        """Get list of registered agent types."""
        return list(self._agents.keys())
    
    async def route_task(
        self,
        task_id: str,
        agent_target: str,
        payload: dict
    ) -> AgentResult:
        """
        Route a task to the appropriate agent and execute.
        
        Args:
            task_id: Task identifier
            agent_target: Target agent type
            payload: Task payload
            
        Returns:
            AgentResult from execution
        """
        agent = self._agents.get(agent_target)
        
        if not agent:
            self.logger.error(f"No agent registered for type: {agent_target}")
            return AgentResult(
                success=False,
                error=f"No agent registered for type: {agent_target}"
            )
        
        self.logger.info(f"Routing task {task_id} to {agent.name}")
        
        return await agent.run(task_id, payload)
    
    async def route_workflow_step(self, workflow_id: str, step: dict) -> AgentResult:
        """
        Route a workflow step to the appropriate agent for execution.
        """
        agent_target = step.get("agent_target")
        agent = self._agents.get(agent_target)

        if not agent:
            self.logger.error(f"No agent registered for workflow step: {agent_target}")
            return AgentResult(
                success=False,
                error=f"No agent registered for workflow step: {agent_target}"
            )

        self.logger.info(f"Routing workflow {workflow_id} step {step.get('step_id')} to {agent.name}")
        return await agent.execute_step(step)
    
    def get_all_statuses(self) -> dict:
        """Get status of all registered agents."""
        return {
            agent_type: agent.get_status()
            for agent_type, agent in self._agents.items()
        }

