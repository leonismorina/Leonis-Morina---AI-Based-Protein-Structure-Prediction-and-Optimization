$docxPath = (Resolve-Path "docs\Udhezues_Mbrojtje_DAA_Leonis_Morina.docx").Path
$pdfPath = [System.IO.Path]::ChangeExtension($docxPath, ".pdf")

$word = New-Object -ComObject Word.Application
$word.Visible = $false
try {
    $doc = $word.Documents.Open($docxPath)
    $doc.SaveAs([ref]$pdfPath, [ref]17)
    $doc.Close()
    Write-Output "Successfully converted to PDF: $pdfPath"
} catch {
    Write-Error $_
} finally {
    $word.Quit()
    [System.Runtime.Interopservices.Marshal]::ReleaseComObject($word) | Out-Null
}
