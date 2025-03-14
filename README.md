# AI DJ Agent System

## Overview

The AI DJ Agent System is an intelligent music programming solution that can autonomously select and play appropriate music, generate engaging commentary, and respond to audience feedback. Designed for versatility, it can adapt to various environments from offices to family events.

The system utilizes the Claude language model from Anthropic to make intelligent decisions, combined with a suite of specialized tools to handle different aspects of music presentation and audience interaction.

## Key Features

- **Contextual Music Selection**: Selects music appropriate to the environment, audience demographics, and time of day
- **Dynamic Announcements**: Generates natural-sounding announcements and song introductions
- **Environment Adaptation**: Can be configured for different settings with environment profiles
- **Audience Engagement**: Tracks and responds to audience feedback and requests
- **Smart Scheduling**: Integrates with event calendars to align music with scheduled activities
- **Multilingual Support**: Translates announcements and content for multilingual audiences
- **Weather-Aware**: Can reference weather conditions in commentary and music selection
- **Song Recognition**: Identifies music from text descriptions or audio samples

## System Architecture

The system uses a modular architecture with two main components:

1. **AI Decision Engine**: Uses Claude to make intelligent decisions about content and audience interaction
2. **Specialized Tools**: A collection of tools for specific functions including:
   - Song Queue Management
   - Music Database
   - Speech Generation
   - Event Calendar
   - Audience Engagement Tracking
   - Weather Information
   - Time Announcements
   - Song Recognition
   - Translation
   - Environment Profiles

## Environment Profiles

The system includes preset environment profiles for different settings:

- **Care Center**: Focus on nostalgia, gentle volume, cognitive stimulation
- **Hospital**: Calming selections, limited announcement volume, wellness themes
- **School**: Age-appropriate content, educational ties, energy management
- **Car Workshop**: Upbeat tempo, industry-appropriate language, ambient volume
- **Mall**: Family-friendly content, shopping-compatible tempo, promotional integration
- **Office**: Work-appropriate selections, productivity focus, time-aware programming
- **Family Events**: Occasion-specific content, celebration themes, dance music
- **Student Dorms**: Contemporary selections, social connection themes, study-time awareness

## Getting Started

### Prerequisites

- Python 3.8+
- Claude API key from Anthropic
- Optional: Additional API keys for weather, song recognition, etc.

### Installation

1. Clone the repository
   ```
   git clone https://github.com/yourusername/ai-dj-agent.git
   cd ai-dj-agent
   ```

2. Install dependencies
   ```
   pip install -r requirements.txt
   ```

3. Configure your API keys
   - Create a `.env` file based on `.env.example`
   - Add your Claude API key and other optional API keys

4. Configure the system
   - Review and update `config.yaml` with your preferences

5. Run the system
   ```
   python main.py
   ```

### Configuration

The system is configured through `config.yaml`. Key configuration options include:

- Claude API settings
- Default environment profile
- Tool-specific configurations
- Announcement frequency and style
- Logging levels

## Extending the System

### Adding New Tools

1. Create a new tool class in the `tools/` directory that inherits from `BaseTool`
2. Implement the required abstract methods
3. Add the tool to your configuration in `config.yaml`

### Creating Custom Environment Profiles

1. Add your profile to `config/environment_profiles.yaml` or
2. Use the `EnvironmentProfileManager` tool to create custom profiles at runtime

## License

[MIT License](LICENSE)

## Acknowledgments

- Anthropic for the Claude API
- Contributors to the open source libraries used in this project