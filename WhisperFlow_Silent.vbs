Set WshShell = CreateObject("WScript.Shell")
Set FSO = CreateObject("Scripting.FileSystemObject")
strDir = FSO.GetParentFolderName(WScript.ScriptFullName)
WshShell.CurrentDirectory = strDir

pythonExe = strDir & "\.venv\Scripts\pythonw.exe"
If Not FSO.FileExists(pythonExe) Then
    pythonExe = "pythonw.exe"
End If

WshShell.Run """" & pythonExe & """ """ & strDir & "\app.py""", 0, False
