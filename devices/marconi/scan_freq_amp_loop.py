print('\n-------o-------')
freq1 = iters[j]
amp1 = amp
cmd.set_var('freq', freq1)
cmd.set_var('amp', amp1)

comm = "python3 devices/marconi/MarconiComm.py"
args = " --freq %.9f --amp %.9f"%(uw_freq1, uw_amp1)
os.system(comm+args)


print('\n')
print('Run #%d/%d, with variables:\nfreq = %g\n'%(j+1, len(iters), freq1))
cmd.run(wait_end=True, add_time=20000)
j += 1
if j == len(iters):
    cmd.stop()


print('\n-------o-------')
uw_freq1 = iters[j]
uw_amp1 = cmd.get_var('uw_amp')
cmd.set_var('uw_freq', uw_freq1)
fr = 1769 + 1e-3*uw_freq1
comm = "python3 devices/marconi/MarconiComm.py"
args = " --freq %.9f --amp %.9f"%(fr, uw_amp1)
os.system(comm+args)
print('\n')
print('Run #%d/%d, with variables:\nuw_freq = %g\n'%(j+1, len(iters), uw_freq1))
cmd.run(wait_end=True, add_time=2000)
j += 1
if j == len(iters):
    cmd.stop()
