from openai import OpenAI
import railtracks as rt

@rt.function_node
def tool_static_map_image_understand(url: str, query: str = "") -> str:
    """
    Read and interpret a static map url with user's preference.
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
                "content": "This is a map showing a target location in the center and its surroundings, and the user wants to open a store on this location. " \
                           "The major point is labeled as \"origin\" in this map. " \
                           "Please read and extract critical information from this map. " \
                           "You can analyze from the perspective of customers, competition, traffic, visibility situation (etc.) of this place. " \
                           "Please provide factual information. If user has a very specific question, only answer the question."
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
