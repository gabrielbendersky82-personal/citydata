import { PLACES_CRITERION, SliderKey, Weights } from "./types";

export interface CriterionInfo {
  key: SliderKey;
  label: string;
  blurb: string;
}

export const CRITERIA: CriterionInfo[] = [
  { key: "safety", label: "Public safety", blurb: "Reported crime, normalized per resident" },
  { key: "affordability", label: "Affordability", blurb: "Home values, rents, rent burden" },
  { key: "socioeconomics", label: "Economy & education", blurb: "Income, jobs, degrees, commutes" },
  { key: "schools", label: "Schools", blurb: "School access and proficiency nearby" },
  { key: "walkability", label: "Walkability", blurb: "Groceries, food, parks within a walk" },
  { key: "transit", label: "Transit", blurb: "Stop density and service frequency" },
  { key: "environment", label: "Health & environment", blurb: "Community health outcomes" },
  { key: "hazard", label: "Natural-hazard risk", blurb: "Flood, heat, storm risk (FEMA)" },
  { key: PLACES_CRITERION, label: "My places", blurb: "Proximity to addresses you pin" },
];

export interface Persona {
  key: string;
  label: string;
  emoji: string;
  weights: Weights;
}

export const PERSONAS: Persona[] = [
  {
    key: "balanced",
    label: "Balanced",
    emoji: "⚖️",
    weights: { safety: 3, affordability: 3, socioeconomics: 3, schools: 3, walkability: 3, transit: 3, environment: 3, hazard: 3, places: 3 },
  },
  {
    key: "family",
    label: "Families",
    emoji: "👨‍👩‍👧",
    weights: { safety: 5, affordability: 3, socioeconomics: 2, schools: 5, walkability: 3, transit: 2, environment: 3, hazard: 3, places: 3 },
  },
  {
    key: "young-professional",
    label: "Young professional",
    emoji: "🎉",
    weights: { safety: 3, affordability: 4, socioeconomics: 2, schools: 0, walkability: 5, transit: 4, environment: 2, hazard: 1, places: 4 },
  },
  {
    key: "budget",
    label: "Budget-first",
    emoji: "💸",
    weights: { safety: 3, affordability: 5, socioeconomics: 1, schools: 1, walkability: 2, transit: 3, environment: 1, hazard: 2, places: 3 },
  },
  {
    key: "retiree",
    label: "Retiree",
    emoji: "🌳",
    weights: { safety: 4, affordability: 3, socioeconomics: 1, schools: 0, walkability: 2, transit: 2, environment: 5, hazard: 3, places: 4 },
  },
];

export const DEFAULT_WEIGHTS: Weights = PERSONAS[0].weights;
