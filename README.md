# "LocalTerm" Gramplet

a Localized index to Gramps Glossary terms

<i><b>This plugin is still in the <big>Experimental</big> stage.</b>  Not feature complete nor ready for general release. Your work done improving a data file is likely to be lost as the gramplet evolves.</i>

This gramplet (available for Dashboard, people-based and Notes view categories), will show you a table of glossary terminology (terms) for Gramps. 
It will show the term, as it appears in the python code, and up to two additional languages tanslations.
The languages are provided in separate Weblate-generated CSV file. One for each language. (However, our CSVs have been modified with additional terms and corrections.) 

Double clicking a row will open a browser page with the Gramps wiki's Glossary in the language of the 2nd column. If the term is unanchored, the local language will be scrolled to the top of page. (Which is a hint that this page has an opportunity for inprovement.) If the anchor exists on the destination page, the browser will be scrolled to the row's term Dictionary for gramps. 

Clicking one of the language columns and start typing will do a search in that column based upon your typing


<img width="794" height="526" alt="image" src="https://github.com/user-attachments/assets/1e4e4857-1a83-4092-9c41-11fdb2d94753" />

## Context menu options

### `Create Note from row` information:

<i>Likely to be outdated.</i>
<img width="917" height="674" alt="image" src="https://github.com/user-attachments/assets/8cb00599-44f6-44df-b200-b32207ca05db" />


### `Copy row to OS Clipboard` information:

Copies the terms in each language and the Glossary URL for the term (from the 2nd column). Intended for pasting into the various Gramps support forums or eMails. 
`Association	Forening	Verknüpfungen	https://gramps-project.org/wiki/index.php/Gramps_Glossary/da#association`

### `Edit source CSV file` action:

Opens whatever app your OS has associated with `.csv` type files. And load the CSV associated with populating the 2nd column. If you choose to edit this file, it is better to save it under a different file name. (These files are in the nameing style and format of exports from Weblate's "Glossary" component.) Then use the Configure to choose the edit file for Language 1 and the original for Language 2. This will let you view the english term, your updated translation, and the original translation; all side-by-side for direct comparision. 

## Congfigure options:

Choose the View -> Configure menu items or click the Configure toolbar icon.

<i>Likely to be outdated.</i>
<img width="695" height="535" alt="image" src="https://github.com/user-attachments/assets/2f32e86f-51a8-4bfe-bafb-78a1908591b9" />
