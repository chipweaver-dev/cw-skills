@echo off
setlocal
set TOOLBOX=%~dp0toolbox\
set ROOT=%~dp0..\..\
pushd "%ROOT%"

rem TODO: add this task's single-purpose scripts in dependency order.
rem The examples below are the usual tail of the pipeline.
rem python "%TOOLBOX%make_film_narration.py" --root . || goto :err
rem python "%TOOLBOX%make_music_bed.py" --root . --force || goto :err
rem python "%TOOLBOX%mix_film_music.py" --root . || goto :err

echo No build steps configured. Edit production\{{VERSION}}\run.bat.
popd
exit /b 0

:err
echo Build failed.
popd
exit /b 1
