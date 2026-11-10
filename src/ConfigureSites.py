"""Local settings window; no network requests are performed here."""
from configparser import RawConfigParser
from Functions.Web.Sites import load_sites, save_sites, DEFAULT_PRIMARY


def build_window(sites, hidden=False):
    import tkinter as tk
    from tkinter import messagebox
    window = tk.Tk()
    if hidden:
        window.withdraw()
    window.title('JavSDT — JavDB 站点设置')
    window.geometry('620x300')
    window.columnconfigure(0, weight=1)
    tk.Label(window, text='主站地址').grid(row=0, column=0, sticky='w', padx=20, pady=(18, 4))
    main_url = tk.Entry(window, width=70)
    main_url.insert(0, sites[0])
    main_url.grid(row=1, column=0, sticky='ew', padx=20)
    tk.Label(window, text='备用站点（每行一个；留空则不使用备用站）').grid(row=2, column=0, sticky='w', padx=20, pady=(14, 4))
    backups = tk.Text(window, height=4, width=70)
    backups.insert('1.0', '\n'.join(sites[1:]))
    backups.grid(row=3, column=0, sticky='ew', padx=20)
    def save():
        try:
            save_sites(main_url.get(), [value for value in backups.get('1.0', 'end').splitlines() if value.strip()])
        except (ValueError, OSError) as error:
            messagebox.showerror('未保存', str(error), parent=window)
            return
        messagebox.showinfo('已保存', '下次整理及补演员时使用新网址。原有整理规则和代理设置保持不变。', parent=window)
        window.destroy()
    tk.Button(window, text='保存站点设置', command=save).grid(row=4, column=0, pady=18)
    return window


def main():
    config = RawConfigParser()
    config.read('【点我设置整理规则】.ini', encoding='utf-8-sig')
    primary = config.get('其他设置', 'javdb网址', fallback=DEFAULT_PRIMARY)
    window = build_window(load_sites(primary))
    window.mainloop()
    return 0
