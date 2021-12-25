# zotero_vscode

## 配置vscode和zotero链接

1. Zotero中安装[BetterBibTeX](https://retorque.re/zotero-better-bibtex)
2. VScode中安装[Citation Picker for Zotero](https://marketplace.visualstudio.com/items?itemName=mblode.zotero)
3. 从此[链接](https://retorque.re/zotero-better-bibtex/exporting/zotero.lua)在工作目录中下载zotero.lua文件
4. 在vscode pandoc插件设置中加入`-s --lua-filter=zotero.lua`字段
5. 在markdown yaml中加入
    ```yaml
    zotero:
        client: zotero
    ```
6. 开始写作