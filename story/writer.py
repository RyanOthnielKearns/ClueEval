from story.story import Story, CharacterStory
from story.random_details import get_random_details
from story.evidence import StoryElement, TypeOfEvidence
from utils.gpt import prompt_completion_chat, prompt_completion_json
from utils.display_interface import display_story_element, display_narrative, display_story_elements
import json

def parse_crime_story(character_name: str, story_text: str) -> CharacterStory:
    lines = story_text.strip().split('\n')
    details = {}
    current_section = None

    for line in lines:
        line = line.replace('**', '')  # Remove all instances of "**"
        if line.startswith('# '):
            current_section = line[2:].lower()
            details[current_section] = []
        elif line.startswith('Motive:'):
            details['motive'] = line.split(':', 1)[1].strip()
        elif line.startswith('Means:'):
            details['means'] = line.split(':', 1)[1].strip()
        elif line.startswith('Opportunity:'):
            details['opportunity'] = line.split(':', 1)[1].strip()
        elif current_section:
            details[current_section].append(line)

    return CharacterStory(
        character_name=character_name,
        means=details['means'],
        motive=details['motive'],
        opportunity=details['opportunity'],
        real_story='\n'.join(details['what happened']),
        story_to_detective='\n'.join(details['explanation to detective'])
    )

def write_stories(story: Story):
    # Load prompt templates
    with open('config/prompts/central_story.txt', 'r') as f:
        central_story_prompt = f.read()
    with open('config/prompts/other_story.txt', 'r') as f:
        other_story_prompt = f.read()

    # Generate the central crime story
    central_prompt = central_story_prompt.replace('{{summary}}', story.summary)
    central_prompt = central_prompt.replace('{{killer}}', story.killer)
    central_prompt = central_prompt.replace('{{victim}}', story.victim)
    crime_story_text = prompt_completion_chat(central_prompt)
    story.crime_story = parse_crime_story(story.killer, crime_story_text)

    # display_narrative(crime_story_text, speaker="Crime Story")
    display_narrative(story.crime_story.__str__(), speaker="Parsed Crime Story")

    # Generate distractor stories for other characters
    # other_characters = [char for char in story.random_people if char not in [story.killer, story.victim]]
    other_characters = []  # Disabling for Development! TODO Reenable
    # murder_summary = f"{story.killer} killed {story.victim} with a {story.crime_weapon} in the {story.crime_location}."
    murder_summary = story.crime_story.real_story
    
    for character in other_characters:
        other_prompt = other_story_prompt.replace('{{summary}}', story.summary)
        other_prompt = other_prompt.replace('{{murder_summary}}', murder_summary)
        other_prompt = other_prompt.replace('{{character}}', character)
        other_prompt = other_prompt.replace('{{other_stories}}', "\n".join([ds.real_story for ds in story.distractor_stories]))
        
        distractor_story_text = prompt_completion_chat(other_prompt)
        distractor_story = parse_crime_story(character, distractor_story_text)
        story.distractor_stories.append(distractor_story)

        # display_narrative(distractor_story_text, speaker=f"Distractor Story {character}")
        display_narrative(distractor_story.__str__(), f"Parsed Story for {character}")

    return story

def convert_story_to_story_elements(story: str) -> list[StoryElement]:
    prompt = f"""
    Convert the following story into a list of story elements. Each element should be a single fact or event from the story, classified according to its relevance to the mystery.

    Story:
    {story}

    Please return a JSON array of objects with the following structure:
    [
        {{
            "text": "The fact or event from the story",
            "type_of_evidence": "supports_guilt" | "proves_guilt" | "supports_innocence" | "proves_innocence"
        }}
    ]

    Classify each element based on how it relates to solving the mystery:
    - "supports_guilt": Suggests but doesn't prove someone's guilt
    - "proves_guilt": Provides definitive proof of guilt
    - "supports_innocence": Suggests but doesn't prove someone's innocence
    - "proves_innocence": Provides definitive proof of innocence

    If an element doesn't clearly fit into these categories, omit it from the results.
    """

    json_response = prompt_completion_json([{"role": "user", "content": prompt}])

    # print(json_response)
    
    if json_response:
        try:
            story_elements = []

            elements = json.loads(json_response)
            if "story_elements" in elements:
                elements = elements["story_elements"]
            for elem in elements:
                # print(elem)
                text = elem['text']
                type_of_evidence = TypeOfEvidence(elem['type_of_evidence'])
                story_elements.append(StoryElement(text=text, type_of_evidence=type_of_evidence))

            return story_elements
        except json.JSONDecodeError:
            print("Error: Invalid JSON response")
        except KeyError:
            print("Error: JSON response missing required keys")
        except ValueError:
            print("Error: Invalid type_of_evidence value")
    
    return []


def main():
    # Get random story details
    story = get_random_details()
    display_story_element(story.summary, title="Story Summary")

    # Write stories
    story = write_stories(story)

    # Convert stories to story elements and display them
    story.crime_story.real_story_elements = convert_story_to_story_elements(story.crime_story.real_story)
    display_story_elements(story.crime_story.real_story_elements, title="Crime Story Real Story Elements")

    story.crime_story.story_to_detective_elements = convert_story_to_story_elements(story.crime_story.story_to_detective)
    display_story_elements(story.crime_story.story_to_detective_elements, title="Crime Story Detective Story Elements")
    
    for i, distractor_story in enumerate(story.distractor_stories):
        distractor_story.real_story_elements = convert_story_to_story_elements(distractor_story.real_story)
        display_story_elements(distractor_story.real_story_elements, title=f"Distractor Story {i+1} Real Story Elements")

        distractor_story.story_to_detective_elements = convert_story_to_story_elements(distractor_story.story_to_detective)
        display_story_elements(distractor_story.story_to_detective_elements, title=f"Distractor Story {i+1} Detective Story Elements")

if __name__ == '__main__':
    main()
