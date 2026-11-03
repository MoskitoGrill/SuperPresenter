# Optional Windows integration check. Only generated test-output documents are opened.
$ErrorActionPreference = 'Stop'
$outputDirectory = [IO.Path]::GetFullPath((Join-Path $PSScriptRoot '../test-output'))
$wordCheckApplication = $null
$wordCheckDocument = $null
try {
    $wordCheckApplication = New-Object -ComObject Word.Application
    $wordCheckApplication.Visible = $false
    $wordCheckApplication.DisplayAlerts = 0
    $wordCheckApplication.AutomationSecurity = 3
    foreach ($stem in @('docx-song', 'docx-template')) {
        $inputPath = Join-Path $outputDirectory ($stem + '.docx')
        $wordCheckDocument = $wordCheckApplication.Documents.Open($inputPath, $false, $false, $false)
        $wordCheckDocument.ExportAsFixedFormat((Join-Path $outputDirectory ($stem + '.pdf')), 17)
        if ($stem -eq 'docx-song') {
            $searchRange = $wordCheckDocument.Content
            if (-not $searchRange.Find.Execute('Český refrén')) { throw 'Generated chorus was not found in Word.' }
            $searchRange.Text = 'Upravený český refrén ve Wordu'
            $searchRange.Bold = -1
            $wordCheckDocument.SaveAs2((Join-Path $outputDirectory 'word-edited.docx'), 16)
        }
        $wordCheckDocument.Close(0)
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($wordCheckDocument)
        $wordCheckDocument = $null
    }
    Write-Output 'Word opened both generated DOCX files, exported PDFs and saved the edited DOCX.'
} finally {
    if ($null -ne $wordCheckDocument) { $wordCheckDocument.Close(0) }
    if ($null -ne $wordCheckApplication) {
        $wordCheckApplication.Quit()
        [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($wordCheckApplication)
    }
}
