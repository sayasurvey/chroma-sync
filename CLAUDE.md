# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

`chroma-sync` — AI/PSDファイルをJPEGに色味を保持しながら変換するWebアプリ（初期段階）。
ローカル、またはWeb上で動作するJPEG変換アプリです。
aiやpsdファイルをjpegに変換すると色の変化が起こる場合があり再度色味の調整が発生します。
それをなくすためのアプリで、変換後の容量をどれくらいまで削減するのかユーザが指定できるようにしたいです。

jpegの色味が変わらないように変換するパッケージ等があればそちらを使い、
jpegの変換自体で色味が変わってしまった場合は色味が変わった部分を自動で戻します。


## 開発環境

環境構築はDockerを使用してください。
