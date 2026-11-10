"""Windows distribution entry point; keep configuration beside the executable."""
import os
from pathlib import Path
import sys
import traceback


def main():
    for stream in (sys.stdout, sys.stderr):
        if stream is not None and hasattr(stream, 'reconfigure'):
            stream.reconfigure(errors='backslashreplace')
    if sys.argv[1:] == ['--self-test']:
        import Youma
        import ActorRepair
        from Functions.Metadata.Genre import better_dict_youma_genres
        from Functions.Progress.Prepare import get_suren_cars
        assert all(better_dict_youma_genres('zh'))
        assert get_suren_cars()
        print('Packaged imports and resources verified.')
        return 0
    print('JavSDT 维护版 9 — 演员关联与已有NFO补全')
    repair_mode = sys.argv[1:2] == ['--repair-actors']
    raw_args = sys.argv[2:] if repair_mode else sys.argv[1:]
    args = [str(Path(raw_args[0]).resolve())] if raw_args else []
    program_dir = Path(sys.executable).parent if getattr(sys, 'frozen', False) else Path(__file__).resolve().parents[1] / 'src'
    os.chdir(program_dir)
    try:
        if not Path('【点我设置整理规则】.ini').exists():
            import CreateIni  # Generates the default configuration only on first launch.
        if repair_mode:
            import ActorRepair
            return ActorRepair.main(args)
        import Youma
        return Youma.main(args)
    except Exception:
        traceback.print_exc()
        return 1
    finally:
        input('\n运行结束，按回车关闭窗口。报错时请复制窗口内容反馈。')


if __name__ == '__main__':
    sys.exit(main())
