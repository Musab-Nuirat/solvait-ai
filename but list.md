Ask Solvait AI – Bug List vs FDD Requirements
Fixed	Not fixed	Further Explanation*

#	FDD Requirement	Observed Bug / Deviation	Evidence
1	Check Leave Balance – The bot should ask “Would you like me to help you request a new leave now?” after showing balances.	The chatbot displays the balances and stops; it does not prompt to request leave.	Balance is returned (annual = 16 days, etc.), but no follow up prompt appears.
2*	Check Leave Balance – Display a structured card with leave type and remaining balance.	Results are returned as plain text without a card layout, reducing readability.	The response lists balances in a single sentence instead of a card.

3	Submit Leave Request – Require confirmation summary before submission.	When a valid leave is parsed (e.g., Arabic sick leave request), the system immediately submits an unpaid leave without showing a summary or asking for confirmation.	“أريد إجازة مرضية لمدة يومين” triggered a submission of unpaid leave without user confirmation.


4	Submit Leave Request – Users can cancel at any step.	Typing “cancel” during the leave request flow results in “I am sorry, I cannot fulfill that request,” showing no cancellation mechanism.	The command “cancel” is rejected instead of cancelling the pending leave request.

5*	Submit Leave Request – Balance validation is mandatory, and users should be informed.	The system validates balances internally but does not show how many days will be deducted or the remaining balance, leaving users uninformed.	The response states only that balance is insufficient and suggests unpaid leave.
6	Submit Leave Request – Confirmation flow should be consistent across languages.	In English, the bot sometimes asks whether to proceed when a conflict exists; in Arabic, it immediately submits once dates are given.	Different behaviors for English vs. Arabic flows were observed, violating consistency.
7	View Payslip – If no month is specified, the bot should ask, “Which month would you like to view?”	For a generic request (“show my payslip”), the bot silently shows the latest payslip instead of prompting for a month.	The payslip appears without clarifying the month, defaulting to January 2026.
8	View Payslip – Provide allowance and deduction summaries.	The bot shows total allowances and deductions but does not break down these categories, contrary to the “summary” requirement.	Only aggregated totals are displayed, omitting individual allowance/deduction details.
9*	View Payslip – Offer a “Download Payslip” button (even if future phase).	No download option, placeholder, or disabled button appears in the UI, so users cannot download or see a forthcoming link.	Lack of download button across all payslip interactions.
10*	Create Excuse – Mandatory fields (reason, type, start and end times).	A general message like “I was late today” sometimes leads to immediate submission of an excuse without asking for time or reason.	The bot returned “Your excuse request has been successfully created” without collecting details.
11	Create Excuse – Consistent data collection.	Inconsistently asks for details: sometimes prompts for arrival time and reason, other times submits directly.	Same input yields different behaviours in separate sessions.
12	Create Excuse – Cancellation option during flow.	There is no mechanism to cancel an excuse request once it’s being created; “cancel” is rejected as an invalid request.	“Cancel” command yields “I am sorry, I cannot fulfill that request”.
13*	General – One confirmed request per flow.	Sending the same message twice or due to page glitches results in duplicate user messages and sometimes duplicate requests, causing data redundancy.	Conversation logs show repeated user messages and multiple identical bot responses.
14	General – Intent isolation between flows.	Context from one flow can leak into another (e.g., payslip or leave request flows interfering with excuse requests).	In some cases, the bot addressed a different intent than the most recent input, suggesting state confusion.

Bugs:
7: It still only defaults to February 2026
 
9: “Download option coming soon!” comes up yet it hasn’t been implemented yet


14: intent wasn’t isolated
  





Explanations:
2: The format changes between the errored form and the fixed form randomly (in both English and Arabic)
  
  
5: it does show the fact that there’s insufficient credits when you apply over your balance however it doesn’t tell you how much balance you have left when the request goes through
 
It should display remaining balance
 



10: It asks why I was late and when I arrived however it never asks about the end times
13: Although it does only show one response when getting multiple instances of the same request, when having multiple lateness requests, it answers as if I already submitted the lateness request rather than confirm it
 
 












Extra:
Not understanding AM/PM asking for the time again, adding 11am again caused it to correctly submit it into the database
 
 
 

Leave should still require conformation even though all the data was provided. Instead, it requests immediately.
 
