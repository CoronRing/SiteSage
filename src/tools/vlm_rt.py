from openai import OpenAI
import railtracks as rt

@rt.function_node
def tool_static_map_image_understand(url: str, query: str = "") -> str:
    """
    Read and interpret a static map url with user's query.
    Args:
        url (str): the url for the static map
        query (Optional[str]): specific query for the interpretation, if not specified, the return would be a general analysis of the static map and center location.
    Returns:
        str: analysis / understanding of the static map catering to user's query.
    """
    client = OpenAI()
    response = client.responses.create(
        model="gpt-5.1",
        reasoning={ "effort": "low" },
        input=[
            {
                "role": "system",
                "content": \
"""This is a map showing a target location labeled as 'A' in the center and its surroundings. \
Your job is to read and extract critical information from this map. \
Based on the target location, you should provide the proximity and orientation of its neighborhood (with name and direction), analyze what kind of location it is at (residential, working, shopping or tourism.) \
You can analyze from the perspective of customers, competition and traffic of this place. \
Only provide factual and objective information without subjectivity such as 'very good' or 'nice'. [[[If user has a specific request, answer the question is your priority.]]] \
Your answer must be less than 500 words."""
            },
            {
                "role": "user",
                "content": [
                    {
                        "type": "input_text",
                        "text": query,
                    },
                    {
                        "type": "input_image",
                        "image_url": url
                    }
                ]
            }
        ]
    )
    return response.output_text
