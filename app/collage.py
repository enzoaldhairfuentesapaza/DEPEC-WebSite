"""Empaqueta hasta seis eventos y cubre los huecos con imágenes decorativas."""

FILLERS=['images/event-comunidad.svg','images/event-servicio.svg']
PORTRAIT_FILLERS=['images/filler-portrait-red.svg','images/filler-portrait-green.svg']

def pack_events(events,columns):
    occupied=set();positions=[]
    for event in events:
        wide=event['d']['orientation']=='landscape'
        width=min(2 if wide else 1,columns);height=1 if wide else 2
        row=0
        while True:
            found=False
            for col in range(columns-width+1):
                cells={(r,c) for r in range(row,row+height) for c in range(col,col+width)}
                if not occupied.intersection(cells):
                    occupied.update(cells)
                    positions.append(dict(row=row+1,column=col+1,rows=height,columns=width))
                    found=True;break
            if found:break
            row+=1
    rows=max((r+1 for r,c in occupied),default=0)
    fillers=[]
    # Agrupa los huecos vecinos en imágenes de hasta 2×2, sin tapar eventos.
    for row in range(rows):
        for col in range(columns):
            if (row,col) in occupied:continue
            choices=[]
            for height in range(1,min(2,rows-row)+1):
                for width in range(1,min(2,columns-col)+1):
                    cells={(r,c) for r in range(row,row+height) for c in range(col,col+width)}
                    if not occupied.intersection(cells):choices.append((height*width,width,height,cells))
            _,width,height,cells=max(choices,key=lambda option:option[:3])
            occupied.update(cells)
            orientation='portrait' if height>width else 'landscape' if width>height else 'square'
            image=(PORTRAIT_FILLERS[len(fillers)%len(PORTRAIT_FILLERS)] if orientation=='portrait' else 'images/filler-square.svg' if orientation=='square' else FILLERS[len(fillers)%len(FILLERS)])
            fillers.append(dict(row=row+1,column=col+1,rows=height,columns=width,image=image,orientation=orientation))
    return positions,fillers

def build_event_collage(events):
    events=list(events)[:6]
    output=[dict(event=event,placements={}) for event in events]
    fillers=[]
    for columns in [4,2,1]:
        positions,decorations=pack_events(events,columns)
        for item,position in zip(output,positions):item['placements'][columns]=position
        fillers.extend(dict(cell,layout=columns) for cell in decorations)
    return dict(events=output,fillers=fillers)
