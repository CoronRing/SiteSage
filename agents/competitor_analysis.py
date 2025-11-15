class agent:
    def __init__(self):
        
    def prompt_system(self):
        prompt = """You are CompetitorAnalysisAgent, an expert in competitor analysis for retail stores. Your task is to analyze potential competitors based on location information and provide insights.

        You have access to the following tools:
        1. Internet Search: To find information about nearby stores and competitors.
        2. Data Analysis: To analyze sales data, customer reviews, and market trends.

        When given a location, you should:
        - Identify potential competitors in the vicinity.
        - Analyze their strengths and weaknesses.
        - Provide recommendations on how to differentiate from these competitors.

        Always ensure your analysis is thorough and backed by data.
        """
        return prompt


class CompetitorAnalysisAgent:
    def __init__(self):
        pass

    def run(self, location_information: dict, context: str):
        """
        Input:
            location_information: dict with store information
            context: information about user request, shared context...

        Output:
            competitors: List, list of potential competitors
            analysis: Str, analysis of competitors

        Process:
            1. The agent takes in location information 
            2. Decide which types of locations will be searched
            3. Based on search result, perform batch processing to evaluate each competitor
            4. Conclusion of the competitor analysis

        Tools:
            during the analysis, the agent is able to access Internet.
        """


    