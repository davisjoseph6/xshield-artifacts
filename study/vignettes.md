\# Vignettes for X-SHIELD Study



\## Scenario s02\_random\_guessing

\*\*Context:\*\* The system detected that the student was randomly guessing answers.  

\*\*Excerpt:\*\* 

```json

{

"trigger":"RANDOM\_GUESSING",

"evidence":\["Random answers detected", "Confidence fluctuated widely"],

"diagnosis":"GUESSING",

"recovery\_action":"EASIER\_ITEMS",

"expected\_effect":"Increase correct answers in next 3 questions",

"teacher\_summary":"The system noticed random guessing behavior and presented easier items to the student."

}



