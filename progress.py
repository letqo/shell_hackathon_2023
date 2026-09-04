import time
def log_progress(sequence, every=None, size=None, name='Items'):
    from ipywidgets import IntProgress, HTML, VBox
    from IPython.display import display

    is_iterator = False
    if size is None:
        try:
            size = len(sequence)
        except TypeError:
            is_iterator = True
    if size is not None:
        if every is None:
            if size <= 200:
                every = 1
            else:
                every = int(size / 200)     # every 0.5%
    else:
        assert every is not None, 'sequence is iterator, set every'

    if is_iterator:
        progress = IntProgress(min=0, max=1, value=1)
        progress.bar_style = 'info'
    else:
        progress = IntProgress(min=0, max=size, value=0)
    label = HTML()
    box = VBox(children=[label, progress])
    display(box)

    index = 0
    try:
        t = time.perf_counter()
        for index, record in enumerate(sequence, 1):
            if index == 1 or index % every == 0:
                if is_iterator:
                    label.value = '{name}: {index} / ?                                    '.format(
                        name=name,
                        index=index
                    )
                else:
                    progress.value = index
                    duration = int((time.perf_counter()-t)*(size-index)/index)
                    label.value = u'{name}: {index} / {size} - {h}h{m}m{s}s to wait'.format(
                        name=name,
                        index=index,
                        size=size,
                        h = duration//3600,
                        m = duration//60-60*(duration//3600),
                        s = duration - 60*(duration//60-60*(duration//3600)) - 3600*(duration//3600)
                    )
            yield record
    except:
        progress.bar_style = 'danger'
        raise
    else:
        progress.bar_style = 'success'
        progress.value = index
        label.value = "{name}: {index}                          ".format(
            name=name,
            index=str(index or '?')
        )

def start():
    for i in log_progress(list(range(10)), every=1):
        time.sleep(1)

start()
