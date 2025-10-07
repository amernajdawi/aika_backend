"""Smart AI-powered link detection for RAG responses."""
import json
import os
from typing import List, Dict, Set, Optional
from pathlib import Path
from openai import AsyncOpenAI
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class LinkDetector:
    """AI-powered link detector that understands user intent."""
    
    def __init__(self):
        """Initialize the AI-powered link detector."""
        # Manager-specified links
        self.manager_links = {
            "water": "https://maps.wisa.bmluk.gv.at/emreg",
            "industry": "https://industry.eea.europa.eu/explore/explore-data-map/map", 
            "nature": "https://natura2000.eea.europa.eu"
        }
        
        # Initialize OpenAI client
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise ValueError("OPENAI_API_KEY environment variable is not set")
        self.client = AsyncOpenAI(api_key=api_key)
    
    
    async def get_relevant_links(self, query: str, chunks: List[Dict], user_onace_code: str = "0") -> List[str]:
        """
        Use AI to understand user intent and provide relevant link based on industry context.
        
        Args:
            query: User's query
            chunks: Retrieved document chunks for additional context
            user_onace_code: Selected industry code (0=General, C=Manufacturing, A=Agriculture, etc.)
            
        Returns:
            List with 0 or 1 relevant link based on AI understanding and industry context
        """
        try:
            # Use AI to classify the query intent with industry context
            topic = await self._classify_query_intent(query, chunks, user_onace_code)
            
            if topic and topic in self.manager_links:
                return [self.manager_links[topic]]
            
            return []
            
        except Exception as e:
            print(f"Error in AI link detection: {e}")
            return []
    
    async def _classify_query_intent(self, query: str, chunks: List[Dict], user_onace_code: str = "0") -> Optional[str]:
        """
        Use AI to classify query intent into water/industry/nature categories with industry context.
        
        Args:
            query: User's query
            chunks: Retrieved document chunks for context
            user_onace_code: Selected industry code for context
            
        Returns:
            Topic category: 'water', 'industry', 'nature', or None
        """
        # Prepare context from chunks
        context_text = ""
        if chunks:
            chunk_texts = [chunk.get('text', '')[:200] for chunk in chunks[:3]]  # First 200 chars of top 3 chunks
            context_text = " ".join(chunk_texts)
        
        # Get industry context
        industry_context = self._get_industry_context(user_onace_code)
        
        # Create AI prompt for intent classification
        system_prompt = """You are an expert at understanding user queries and classifying them into specific categories.

You have access to 3 specific links with detailed information:

1. WATER: https://maps.wisa.bmluk.gv.at/emreg 
   - EMREG (Environmental Monitoring and Reporting System)
   - Austrian water quality maps and monitoring data
   - Groundwater, surface water, drinking water quality
   - Water contamination levels, aquatic ecosystem health
   - River, lake, and stream water quality assessments
   - Water management and monitoring tools

2. INDUSTRY: https://industry.eea.europa.eu/explore/explore-data-map/map
   - European Industrial Emissions Portal
   - Industrial facility emissions data and reporting
   - Manufacturing pollution tracking and monitoring
   - Factory environmental impact reporting
   - Industrial emissions compliance and requirements
   - Production facility environmental data

3. NATURE: https://natura2000.eea.europa.eu
   - Natura 2000 Network Viewer
   - European biodiversity and protected areas network
   - Wildlife habitat conservation information
   - Protected species and ecosystem data
   - Environmental protection and conservation measures
   - Biodiversity monitoring and assessment tools

Your task is to analyze the user's query and determine if it relates to:
- WATER: Water quality, water management, freshwater, aquatic environments, rivers, lakes, groundwater, drinking water, water monitoring, EMREG, water contamination, aquatic health
- INDUSTRY: Industrial emissions, manufacturing pollution, factory emissions, industrial facilities, production emissions, industrial data, facility reporting, environmental compliance
- NATURE: Biodiversity, Natura 2000, protected areas, wildlife, habitat conservation, environmental protection, ecosystems, species protection, nature conservation

Respond with ONLY one word: "water", "industry", "nature", or "none" if the query doesn't clearly relate to any of these three categories.

Be intelligent and understand context, not just keywords. Consider the user's actual intent and what they want to accomplish."""

        user_prompt = f"""User Query: "{query}"

Industry Context: {industry_context}

Context from relevant documents:
{context_text}

Classify this query into one of the three categories, considering the user's industry context."""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4.1-mini-2025-04-14",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.0,
                max_tokens=10
            )
            
            classification = response.choices[0].message.content.strip().lower()
            
            # Validate the classification
            if classification in ["water", "industry", "nature"]:
                return classification
            else:
                return None
                
        except Exception as e:
            print(f"Error in AI classification: {e}")
            return None
    
    def _get_industry_context(self, onace_code: str) -> str:
        """
        Get industry context description based on ÖNACE code.
        
        Args:
            onace_code: ÖNACE industry code
            
        Returns:
            Industry context description
        """
        industry_contexts = {
            "0": "General - All industries and sectors",
            "A": "Agriculture, Forestry and Fishing - Farming, crop production, livestock, forestry",
            "B": "Mining and Quarrying - Extraction of minerals, oil, gas",
            "C": "Manufacturing - Production of goods, factories, industrial facilities",
            "D": "Electricity, Gas, Steam and Air Conditioning Supply - Energy production",
            "E": "Water Supply; Sewerage, Waste Management and Remediation Activities - Water management, waste treatment",
            "F": "Construction - Building, infrastructure, construction activities",
            "G": "Wholesale and Retail Trade; Repair of Motor Vehicles and Motorcycles - Trading, retail",
            "H": "Transportation and Storage - Logistics, transport, shipping",
            "I": "Accommodation and Food Service Activities - Hotels, restaurants, tourism",
            "J": "Information and Communication - IT, telecommunications, media",
            "K": "Financial and Insurance Activities - Banking, insurance, financial services",
            "L": "Real Estate Activities - Property, real estate",
            "M": "Professional, Scientific and Technical Activities - Consulting, research, professional services",
            "N": "Administrative and Support Service Activities - Administrative services",
            "O": "Public Administration and Defence; Compulsory Social Security - Government, public sector",
            "P": "Education - Schools, universities, training",
            "Q": "Human Health and Social Work Activities - Healthcare, social services",
            "R": "Arts, Entertainment and Recreation - Entertainment, culture, sports",
            "S": "Other Service Activities - Other services",
            "T": "Activities of Households as Employers; Undifferentiated Goods- and Services-Producing Activities of Households for Own Use",
            "U": "Activities of Extraterritorial Organisations and Bodies - International organizations"
        }
        
        return industry_contexts.get(onace_code, f"Industry code {onace_code} - Unknown sector")
    
    def get_links_for_topic(self, topic: str) -> List[str]:
        """Get link for a specific topic."""
        topic_lower = topic.lower()
        if topic_lower in self.manager_links:
            return [self.manager_links[topic_lower]]
        return []
    
    def get_all_topics(self) -> List[str]:
        """Get all available topics."""
        return list(self.manager_links.keys())

# Global instance
link_detector = LinkDetector()
